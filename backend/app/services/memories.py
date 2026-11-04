import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Engine, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import (
    Document,
    Entity,
    EntityAlias,
    EntityRelation,
    Meeting,
    Memory,
    Message,
    User,
)
from app.db.session import session_factory
from app.schemas.documents import SourceCitation
from app.schemas.meetings import Evidence, MeetingExtraction, MemoryClaim
from app.schemas.memories import (
    AliasRequest,
    Correction,
    EntityOut,
    ImportResult,
    MemoryOut,
    MergeRequest,
    RecallResult,
)
from app.services.audit import audit
from app.services.llm.provider import ChatError
from app.services.pdf import lexical_text
from app.services.storage import PrivateStorage
from app.services.transcripts import normalize_due, parse_txt, validate_evidence


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def key_for(*values: object) -> str:
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, default=str).encode()
    ).hexdigest()


def slot_for(predicate: str, value: str) -> str:
    return (
        predicate
        if predicate in ("owner", "deadline", "role", "location")
        else predicate + ":" + key_for(normalized(value))
    )


class MemoryService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.sessions, self.settings = session_factory(engine), settings

    def entity(self, db: Session, owner: UUID, name: str, kind: str) -> Entity:
        name = " ".join(unicodedata.normalize("NFKC", name).split())
        token = normalized(name)
        if not token or len(token) > 180:
            raise ChatError(
                "ENTITY_NAME_INVALID", "Entity name must be 1–180 characters.", 422
            )
        alias = db.scalar(
            select(EntityAlias).where(
                EntityAlias.user_id == owner,
                EntityAlias.type == kind,
                EntityAlias.normalized_name == token,
            )
        )
        if alias:
            row = db.get(Entity, alias.entity_id)
            assert row and row.user_id == owner
            return row
        row = Entity(
            user_id=owner, type=kind, canonical_name=name, normalized_name=token
        )
        db.add(row)
        db.flush()
        db.add(
            EntityAlias(
                user_id=owner,
                entity_id=row.id,
                type=kind,
                name=name,
                normalized_name=token,
                confirmed_by_user=False,
            )
        )
        db.flush()
        return row

    def entity_owned(self, db: Session, owner: UUID, identifier: UUID) -> Entity:
        row = db.scalar(
            select(Entity)
            .where(Entity.id == identifier, Entity.user_id == owner)
            .with_for_update()
        )
        if row is None:
            raise ChatError("NOT_FOUND", "Entity not found.", 404)
        if row.merged_into_id:
            raise ChatError(
                "ENTITY_MERGED",
                "Use the canonical target entity after this merge.",
                409,
            )
        return row

    def owned(self, db: Session, owner: UUID, identifier: UUID) -> Memory:
        row = db.scalar(
            select(Memory)
            .where(Memory.id == identifier, Memory.user_id == owner)
            .with_for_update()
        )
        if row is None:
            raise ChatError("NOT_FOUND", "Memory not found.", 404)
        return row

    def refresh_search(self, db: Session, owner: UUID) -> None:
        entities = {
            e.id: e for e in db.scalars(select(Entity).where(Entity.user_id == owner))
        }
        aliases: dict[UUID, list[str]] = defaultdict(list)
        for alias in db.scalars(
            select(EntityAlias).where(EntityAlias.user_id == owner)
        ):
            aliases[alias.entity_id].append(alias.name)
        for row in db.scalars(select(Memory).where(Memory.user_id == owner)):
            names = aliases[row.subject_entity_id]
            target = row.value_json.get("object_entity_id")
            if target:
                names = [*names, *aliases.get(UUID(str(target)), [])]
            row.search_text = lexical_text(
                " ".join(
                    [
                        entities[row.subject_entity_id].canonical_name,
                        *names,
                        row.predicate,
                        str(row.value_json["text"]),
                        row.evidence_quote,
                    ]
                )
            )

    def recompute(self, db: Session, owner: UUID, entity_id: UUID, slot: str) -> None:
        rows = list(
            db.scalars(
                select(Memory).where(
                    Memory.user_id == owner,
                    Memory.subject_entity_id == entity_id,
                    Memory.slot_key == slot,
                )
            )
        )
        times: dict[datetime, list[Memory]] = defaultdict(list)
        for row in rows:
            if row.lifecycle != "recorded":
                row.status = row.lifecycle
            if row.valid_from is None or row.review_state != "confirmed":
                if row.lifecycle == "recorded":
                    row.status = "needs_review"
                continue
            times[row.valid_from].append(row)
        ordered = sorted(times)
        for index, when in enumerate(ordered):
            group = times[when]
            end = ordered[index + 1] if index + 1 < len(ordered) else None
            values = {
                normalized(str(row.value_json["text"]))
                for row in group
                if row.lifecycle == "recorded"
            }
            for row in group:
                row.valid_to = end
                if row.lifecycle == "recorded":
                    row.status = (
                        "conflict"
                        if len(values) > 1
                        else "superseded"
                        if end
                        else "active"
                    )

    def record(
        self, db: Session, owner: UUID, meeting: Meeting, claim: MemoryClaim
    ) -> Memory | None:
        evidence = claim.evidence
        subject = self.entity(db, owner, claim.subject, claim.subject_type)
        value = claim.value.strip()
        supported = True
        if (
            normalized(claim.subject) not in normalized(evidence.quote)
            and claim.predicate != "fact"
        ):
            return None
        if claim.predicate == "deadline":
            # Model dates are never trusted over a source-supported calendar value.
            due = normalize_due(value, meeting.occurred_at, meeting.timezone)
            if value not in evidence.quote:
                return None
            if due is None:
                supported = False
            else:
                from zoneinfo import ZoneInfo

                value = (
                    due.astimezone(ZoneInfo(meeting.timezone or "UTC"))
                    .date()
                    .isoformat()
                )
        elif claim.predicate != "fact" and normalized(value) not in normalized(
            evidence.quote
        ):
            return None
        source_key = key_for(
            owner,
            meeting.id,
            normalized(claim.subject),
            claim.predicate,
            normalized(value),
            evidence.line_start,
            evidence.line_end,
            evidence.quote,
        )
        if db.scalar(
            select(Memory.id).where(
                Memory.user_id == owner, Memory.source_key == source_key
            )
        ):
            return None
        payload: dict[str, object] = {"text": value}
        target = None
        if claim.predicate == "owner":
            # No ownership inferred merely because a person's name occurs in a line.
            if not re.search(
                r"\b(own|owns|owner|responsible)\b|负责", evidence.quote, re.IGNORECASE
            ):
                return None
            target = self.entity(db, owner, value, "person")
            payload["object_entity_id"] = str(target.id)
            payload["text"] = target.canonical_name
        review = (
            "confirmed"
            if meeting.occurred_at and evidence.kind == "explicit_fact" and supported
            else "needs_review"
        )
        row = Memory(
            user_id=owner,
            subject_entity_id=subject.id,
            predicate=claim.predicate,
            slot_key=slot_for(claim.predicate, value),
            value_json=payload,
            memory_type="episodic" if claim.predicate == "fact" else "semantic",
            valid_from=meeting.occurred_at,
            source_type="meeting",
            source_id=meeting.id,
            meeting_id=meeting.id,
            evidence_quote=evidence.quote,
            line_start=evidence.line_start,
            line_end=evidence.line_end,
            confidence=0.8 if evidence.kind == "explicit_fact" else 0.5,
            evidence_kind=evidence.kind,
            review_state=review,
            status="needs_review",
            source_key=source_key,
            search_text="",
        )
        db.add(row)
        db.flush()
        if target:
            db.add(
                EntityRelation(
                    user_id=owner,
                    from_entity_id=subject.id,
                    to_entity_id=target.id,
                    relation=claim.predicate,
                    memory_id=row.id,
                )
            )
        return row

    def write_meeting(
        self, db: Session, meeting: Meeting, analysis: MeetingExtraction, text: str
    ) -> int:
        owner = meeting.user_id
        db.scalar(select(User).where(User.id == owner).with_for_update())
        claims = list(analysis.memory_claims)
        people = {p.name for p in analysis.people}
        for name in people:
            self.entity(db, owner, name, "person")
        if meeting.location:
            self.entity(db, owner, meeting.location, "place")
        lines = text.splitlines()
        projects: set[str] = {c.subject for c in claims if c.subject_type == "project"}
        # Conservative literal adapters support historical Phase 3 analysis without
        # a second LLM call. No fuzzy person matching or implicit aliases.
        for i, line in enumerate(lines, 1):
            speaker, _, content = line.partition(":")
            person = speaker.strip() if speaker.strip() in people else None
            match = re.match(
                r"\s*I own (?:the )?([A-Za-z][A-Za-z0-9_-]{1,50})\b", content
            )
            if match and person:
                project = match[1]
                projects.add(project)
                claims.append(
                    MemoryClaim(
                        subject=project,
                        subject_type="project",
                        predicate="owner",
                        value=person,
                        evidence=Evidence(
                            line_start=i, line_end=i, quote=line, kind="explicit_fact"
                        ),
                    )
                )
            for name in people:
                match = re.search(
                    re.escape(name)
                    + (
                        " (?:owns|is responsible for) (?:the )?([A-Za-z][A-"
                        "Za-z0-9_-]{1,50})\\b"
                    ),
                    line,
                )
                if match:
                    projects.add(match[1])
                    claims.append(
                        MemoryClaim(
                            subject=match[1],
                            subject_type="project",
                            predicate="owner",
                            value=name,
                            evidence=Evidence(
                                line_start=i,
                                line_end=i,
                                quote=line,
                                kind="explicit_fact",
                            ),
                        )
                    )
            match = re.search(
                (
                    "\\b([A-Za-z][A-Za-z0-9_-]{1,50})\\s+(?:deadline|deli"
                    "very date|due date)\\b"
                ),
                content,
                re.IGNORECASE,
            )
            if match:
                projects.add(match[1])
        for i, line in enumerate(lines, 1):
            for project in projects:
                if normalized(project) not in normalized(line) or not re.search(
                    r"\b(due|deadline|deliver|delivery)\b|截止|交付",
                    line,
                    re.IGNORECASE,
                ):
                    continue
                dates = re.findall(
                    (
                        "\\b\\d{4}-\\d{2}-\\d{2}\\b|\\b(?:Nov(?:ember)?|Dec(?:emb"
                        "er)?|Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:i"
                        "l)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:temb"
                        "er)?|Oct(?:ober)?) \\d{1,2}(?:, \\d{4})?\\b"
                    ),
                    line,
                )
                if len(dates) == 1:
                    claims.append(
                        MemoryClaim(
                            subject=project,
                            subject_type="project",
                            predicate="deadline",
                            value=dates[0],
                            evidence=Evidence(
                                line_start=i,
                                line_end=i,
                                quote=line,
                                kind="explicit_fact",
                            ),
                        )
                    )
        for fact in analysis.candidate_facts:
            if not any(
                c.predicate != "fact"
                and c.evidence.line_start <= fact.evidence.line_end
                and c.evidence.line_end >= fact.evidence.line_start
                for c in claims
            ):
                claims.append(
                    MemoryClaim(
                        subject=meeting.title,
                        subject_type="topic",
                        predicate="fact",
                        value=fact.text,
                        evidence=fact.evidence,
                    )
                )
        # Preserve decisions, risks and commitments as dated source events.
        for value, evidence in [
            *((item.text, item.evidence) for item in analysis.decisions),
            *((item.title, item.evidence) for item in analysis.risks),
            *((item.title, item.evidence) for item in analysis.tasks),
        ]:
            claims.append(
                MemoryClaim(
                    subject=meeting.title,
                    subject_type="topic",
                    predicate="fact",
                    value=value,
                    evidence=evidence,
                )
            )
        inserted = 0
        slots: set[tuple[UUID, str]] = set()
        for claim in claims:
            row = self.record(db, owner, meeting, claim)
            if row:
                inserted += 1
                slots.add((row.subject_entity_id, row.slot_key))
        db.flush()
        for entity_id, slot in slots:
            self.recompute(db, owner, entity_id, slot)
        self.refresh_search(db, owner)
        if inserted:
            audit(db, owner, "memories_recorded", "meeting", meeting.id, count=inserted)
        return inserted

    def source(self, db: Session, row: Memory, label: int = 1) -> SourceCitation | None:
        if row.message_id:
            message = db.get(Message, row.message_id)
            if not message or message.user_id != row.user_id:
                return None
            prefix = (
                (
                    "User correction; original message is not proof of "
                    "the corrected value. "
                )
                if row.source_type == "user_correction"
                else "Explicit user assertion. "
            )
            return SourceCitation(
                key=f"memory:{row.id}",
                label=label,
                filename="Saved conversation",
                excerpt=(
                    f"{prefix}Stored {row.predicate}: {row.value_json['text']}. "
                    f"Status: {row.status}. Evidence: {row.evidence_quote}"
                ),
                source_type="user_correction"
                if row.source_type == "user_correction"
                else "chat_evidence",
                score=row.confidence,
                memory_id=row.id,
                occurred_at=message.created_at,
                line_start=1,
                line_end=1,
                memory_status=row.status,
                conversation_id=message.conversation_id,
                message_id=message.id,
            )
        meeting = db.get(Meeting, row.meeting_id) if row.meeting_id else None
        doc = db.get(Document, meeting.document_id) if meeting else None
        if not meeting or not doc or doc.user_id != row.user_id:
            return None
        annotation = (
            "User correction; original evidence is not proof of the corrected value. "
            if row.source_type == "user_correction"
            else ""
        )
        excerpt = (
            f"{annotation}Stored {row.predicate}: {row.value_json['text']}. "
            f"Status: {row.status}. Evidence: {row.evidence_quote}"
        )
        return SourceCitation(
            key=f"memory:{row.id}",
            label=label,
            document_id=doc.id,
            filename=doc.filename,
            excerpt=excerpt,
            source_type="user_correction"
            if row.source_type == "user_correction"
            else "meeting_evidence",
            score=row.confidence,
            meeting_id=meeting.id,
            memory_id=row.id,
            occurred_at=meeting.occurred_at,
            timezone=meeting.timezone,
            date_precision=str(meeting.metadata_json.get("date_precision", "unknown")),
            line_start=row.line_start,
            line_end=row.line_end,
            memory_status=row.status,
        )

    def out(self, db: Session, row: Memory) -> MemoryOut:
        entity = db.get(Entity, row.subject_entity_id)
        assert entity
        return MemoryOut.model_validate(row).model_copy(
            update={
                "subject_name": entity.canonical_name,
                "source": self.source(db, row),
            }
        )

    def listing(
        self,
        owner: UUID,
        entity_id: UUID | None = None,
        status: str | None = None,
        memory_type: str | None = None,
        valid_at: datetime | None = None,
        limit: int = 200,
    ) -> list[MemoryOut]:
        with self.sessions() as db:
            q = select(Memory).where(Memory.user_id == owner)
            if entity_id:
                q = q.where(Memory.subject_entity_id == entity_id)
            if status:
                q = q.where(Memory.status == status)
            if memory_type:
                q = q.where(Memory.memory_type == memory_type)
            if valid_at:
                q = q.where(
                    Memory.valid_from <= valid_at,
                    or_(Memory.valid_to.is_(None), Memory.valid_to > valid_at),
                )
            return [
                self.out(db, row)
                for row in db.scalars(
                    q.order_by(Memory.observed_at.desc(), Memory.id).limit(limit)
                )
            ]

    def entities(self, owner: UUID) -> list[EntityOut]:
        with self.sessions() as db:
            aliases: dict[UUID, list[str]] = defaultdict(list)
            for alias in db.scalars(
                select(EntityAlias).where(EntityAlias.user_id == owner)
            ):
                aliases[alias.entity_id].append(alias.name)
            return [
                EntityOut(
                    id=e.id,
                    type=e.type,
                    canonical_name=e.canonical_name,
                    revision=e.revision,
                    aliases=aliases[e.id],
                    merged_into_id=e.merged_into_id,
                )
                for e in db.scalars(
                    select(Entity)
                    .where(Entity.user_id == owner, Entity.merged_into_id.is_(None))
                    .order_by(Entity.canonical_name)
                )
            ]

    def alias(self, owner: UUID, identifier: UUID, body: AliasRequest) -> EntityOut:
        with self.sessions.begin() as db:
            db.scalar(select(User).where(User.id == owner).with_for_update())
            row = self.entity_owned(db, owner, identifier)
            if row.revision != body.revision:
                raise ChatError(
                    "ENTITY_REVISION_CHANGED",
                    "Reload the entity before confirming identity.",
                    409,
                )
            token = normalized(body.alias)
            if not token:
                raise ChatError("ENTITY_NAME_INVALID", "Alias cannot be blank.", 422)
            previous = db.scalar(
                select(EntityAlias).where(
                    EntityAlias.user_id == owner,
                    EntityAlias.type == row.type,
                    EntityAlias.normalized_name == token,
                )
            )
            if previous and previous.entity_id != identifier:
                raise ChatError(
                    "ENTITY_ALIAS_CONFLICT",
                    "Name belongs to another entity. Review an explicit merge instead.",
                    409,
                )
            if not previous:
                db.add(
                    EntityAlias(
                        user_id=owner,
                        entity_id=identifier,
                        type=row.type,
                        name=body.alias.strip(),
                        normalized_name=token,
                        confirmed_by_user=True,
                    )
                )
                row.revision += 1
                db.flush()
                self.refresh_search(db, owner)
                audit(db, owner, "entity_alias_confirmed", "entity", identifier)
        return next(e for e in self.entities(owner) if e.id == identifier)

    def merge(self, owner: UUID, identifier: UUID, body: MergeRequest) -> EntityOut:
        if identifier == body.target_id:
            raise ChatError("ENTITY_MERGE_INVALID", "Select a different target.", 422)
        with self.sessions.begin() as db:
            db.scalar(select(User).where(User.id == owner).with_for_update())
            source = self.entity_owned(db, owner, identifier)
            target = self.entity_owned(db, owner, body.target_id)
            if source.revision != body.revision or source.type != target.type:
                raise ChatError(
                    "ENTITY_MERGE_INVALID",
                    "Reload and confirm two entities of the same type.",
                    409,
                )
            for alias in db.scalars(
                select(EntityAlias).where(
                    EntityAlias.user_id == owner, EntityAlias.entity_id == identifier
                )
            ):
                alias.entity_id, alias.confirmed_by_user = target.id, True
            affected: set[tuple[UUID, str]] = set()
            for row in db.scalars(select(Memory).where(Memory.user_id == owner)):
                changed = False
                if row.subject_entity_id == identifier:
                    row.subject_entity_id = target.id
                    changed = True
                    affected.add((target.id, row.slot_key))
                if row.value_json.get("object_entity_id") == str(identifier):
                    row.value_json = {
                        **row.value_json,
                        "object_entity_id": str(target.id),
                        "text": target.canonical_name,
                    }
                    affected.add((row.subject_entity_id, row.slot_key))
                    changed = True
                if changed:
                    row.revision += 1
            for relation in db.scalars(
                select(EntityRelation).where(EntityRelation.user_id == owner)
            ):
                if relation.from_entity_id == identifier:
                    relation.from_entity_id = target.id
                if relation.to_entity_id == identifier:
                    relation.to_entity_id = target.id
            source.merged_into_id = target.id
            source.revision += 1
            target.revision += 1
            db.flush()
            for entity_id, slot in affected:
                self.recompute(db, owner, entity_id, slot)
            self.refresh_search(db, owner)
            audit(
                db,
                owner,
                "entities_merged",
                "entity",
                identifier,
                target_id=str(target.id),
            )
        return next(e for e in self.entities(owner) if e.id == body.target_id)

    def correct(self, owner: UUID, identifier: UUID, body: Correction) -> MemoryOut:
        with self.sessions.begin() as db:
            db.scalar(select(User).where(User.id == owner).with_for_update())
            old = self.owned(db, owner, identifier)
            if old.revision != body.revision or old.lifecycle != "recorded":
                raise ChatError(
                    "MEMORY_REVISION_CHANGED",
                    "Memory changed or is revoked; reload before correcting.",
                    409,
                )
            start = body.valid_from or old.valid_from
            if start is None:
                raise ChatError(
                    "MEMORY_DATE_REQUIRED",
                    "Confirm an effective time with UTC offset.",
                    422,
                )
            subject = self.entity_owned(
                db, owner, body.subject_entity_id or old.subject_entity_id
            )
            value = body.value.strip()
            if not value:
                raise ChatError("MEMORY_VALUE_INVALID", "Value cannot be blank.", 422)
            if old.predicate == "deadline":
                try:
                    value = date.fromisoformat(value).isoformat()
                except ValueError as exc:
                    raise ChatError(
                        "MEMORY_VALUE_INVALID",
                        "Use YYYY-MM-DD for a corrected deadline.",
                        422,
                    ) from exc
            payload: dict[str, object] = {"text": value}
            target = (
                self.entity(db, owner, value, "person")
                if old.predicate == "owner"
                else None
            )
            if target:
                payload["object_entity_id"] = str(target.id)
                payload["text"] = target.canonical_name
            row = Memory(
                user_id=owner,
                subject_entity_id=subject.id,
                predicate=old.predicate,
                slot_key=slot_for(old.predicate, value),
                value_json=payload,
                memory_type=old.memory_type,
                valid_from=start,
                source_type="user_correction",
                source_id=old.id,
                meeting_id=old.meeting_id,
                message_id=old.message_id,
                evidence_quote=old.evidence_quote,
                line_start=old.line_start,
                line_end=old.line_end,
                confidence=1,
                evidence_kind="explicit_fact",
                review_state="confirmed",
                status="active",
                supersedes_id=old.id,
                correction_reason=body.reason,
                source_key=key_for(old.id, old.revision, "user-correction"),
                search_text="",
            )
            old.lifecycle, old.status = "corrected", "corrected"
            old.revision += 1
            db.add(row)
            db.flush()
            if target:
                db.add(
                    EntityRelation(
                        user_id=owner,
                        from_entity_id=subject.id,
                        to_entity_id=target.id,
                        relation=old.predicate,
                        memory_id=row.id,
                    )
                )
            self.recompute(db, owner, old.subject_entity_id, old.slot_key)
            self.recompute(db, owner, subject.id, row.slot_key)
            self.refresh_search(db, owner)
            audit(
                db,
                owner,
                "memory_corrected",
                "memory",
                old.id,
                replacement_id=str(row.id),
                previous_revision=body.revision,
            )
            result = self.out(db, row)
        return result

    def revoke(self, owner: UUID, identifier: UUID, revision: int) -> None:
        with self.sessions.begin() as db:
            db.scalar(select(User).where(User.id == owner).with_for_update())
            row = self.owned(db, owner, identifier)
            if row.lifecycle == "revoked":
                return
            if row.revision != revision or row.lifecycle != "recorded":
                raise ChatError(
                    "MEMORY_REVISION_CHANGED", "Reload the memory before revoking.", 409
                )
            row.lifecycle, row.status = "revoked", "revoked"
            row.revision += 1
            self.recompute(db, owner, row.subject_entity_id, row.slot_key)
            audit(db, owner, "memory_revoked", "memory", identifier)

    def import_meetings(self, owner: UUID, after: UUID | None = None) -> ImportResult:
        inserted = 0
        with self.sessions.begin() as db:
            db.scalar(select(User).where(User.id == owner).with_for_update())
            q = (
                select(Meeting, Document)
                .join(Document, Meeting.document_id == Document.id)
                .where(Meeting.user_id == owner, Document.status == "ready")
            )
            if after:
                q = q.where(Meeting.id > after)
            batch = list(db.execute(q.order_by(Meeting.id).limit(201)))
            rows = batch[:200]
            processed = 0
            for meeting, doc in rows:
                try:
                    data = (
                        PrivateStorage(self.settings.storage_root)
                        .path(doc.storage_key)
                        .read_bytes()
                    )
                except OSError as exc:
                    raise ChatError(
                        "MEETING_SOURCE_MISSING",
                        (
                            "Original TXT is unavailable. Restore private stora"
                            "ge before importing."
                        ),
                        409,
                    ) from exc
                if hashlib.sha256(data).hexdigest() != doc.checksum:
                    raise ChatError(
                        "MEETING_SOURCE_CHANGED",
                        "Source changed; import stopped without partial publication.",
                        409,
                    )
                text, lines = parse_txt(data, self.settings.meeting_max_upload_bytes)
                analysis = MeetingExtraction.model_validate(meeting.analysis_json)
                validate_evidence(analysis, lines)
                inserted += self.write_meeting(db, meeting, analysis, text)
                processed += 1
        return ImportResult(
            processed=processed,
            inserted=inserted,
            next_cursor=rows[-1][0].id if len(batch) > 200 else None,
        )

    def recall(
        self, owner: UUID, question: str, only: str | None = None, language: str = "en"
    ) -> RecallResult:
        query = normalized(question)
        asks_date = bool(re.search(r"deadline|\bdue\b|截止|交付|到期", query))
        asks_owner = bool(
            re.search(r"\b(owner|owns?|responsible)\b|负责人|谁负责|由谁", query)
        )
        predicate = only or (
            "deadline" if asks_date else "owner" if asks_owner else None
        )
        with self.sessions() as db:
            aliases = list(
                db.scalars(select(EntityAlias).where(EntityAlias.user_id == owner))
            )
            matched = {
                a.entity_id
                for a in aliases
                if re.search(
                    r"(?<![a-z0-9])" + re.escape(a.normalized_name) + r"(?![a-z0-9])",
                    query,
                )
            }
            if predicate:
                projects = {
                    identifier
                    for identifier in matched
                    if (entity := db.get(Entity, identifier))
                    and entity.type == "project"
                }
                if len(projects) == 1:
                    matched = projects
                if len(matched) != 1:
                    return RecallResult(
                        direct=True,
                        answer=(
                            "记忆无法确定唯一主体，请明确项目或人物名称。"
                            if language == "zh"
                            else "Stored memory does not identify one unambiguous "
                            "subject. Name the project/person explicitly."
                        ),
                        sources=[],
                        memory_ids=[],
                    )
                entity_id = next(iter(matched))
                entity = db.get(Entity, entity_id)
                assert entity
                if asks_date and asks_owner and only is None:
                    first, second = (
                        self.recall(owner, question, "owner", language),
                        self.recall(owner, question, "deadline", language),
                    )
                    offset = len(first.sources)
                    shifted = re.sub(
                        r"\[(\d+)\]",
                        lambda match: f"[{int(match[1]) + offset}]",
                        second.answer or "",
                    )
                    sources = [
                        *first.sources,
                        *[
                            s.model_copy(update={"label": s.label + offset})
                            for s in second.sources
                        ],
                    ]
                    return RecallResult(
                        direct=True,
                        answer=(first.answer or "") + "\n" + shifted,
                        sources=sources,
                        memory_ids=[*first.memory_ids, *second.memory_ids],
                    )
                history = only != "owner" and bool(
                    re.search(
                        r"history|change|from|timeline|历史|变化|过程|改为", query
                    )
                )
                q = select(Memory).where(
                    Memory.user_id == owner,
                    Memory.predicate == predicate,
                    Memory.lifecycle == "recorded",
                    Memory.review_state == "confirmed",
                )
                if predicate == "owner" and entity.type == "person":
                    q = q.join(
                        EntityRelation, EntityRelation.memory_id == Memory.id
                    ).where(
                        EntityRelation.user_id == owner,
                        EntityRelation.to_entity_id == entity.id,
                    )
                else:
                    q = q.where(Memory.subject_entity_id == entity.id)
                all_rows = list(
                    db.scalars(
                        q.order_by(Memory.valid_from, Memory.observed_at, Memory.id)
                    )
                )
                active = [r for r in all_rows if r.status == "active"]
                conflicts = [
                    r for r in all_rows if r.status == "conflict" and r.valid_to is None
                ]
                unique = {
                    (
                        r.valid_from,
                        r.subject_entity_id,
                        normalized(str(r.value_json["text"])),
                        r.source_type,
                    ): r
                    for r in (all_rows if history else conflicts or active)
                }
                rows = list(unique.values())[-8:]
                optional_sources = [
                    self.source(db, row, i) for i, row in enumerate(rows, 1)
                ]
                citations = [s for s in optional_sources if s is not None]
                if not rows:
                    answer = (
                        "No active, source-supported memory establishes thi"
                        "s answer. Deleted/uncertain facts are not restored"
                        " from older records."
                    )
                elif conflicts:
                    answer = (
                        "Conflicting observations require review; no curren"
                        "t value was selected. "
                    ) + "; ".join(
                        f"{r.value_json['text']} [{i}]" for i, r in enumerate(rows, 1)
                    )
                else:

                    def display(value: str) -> str:
                        try:
                            parsed = date.fromisoformat(value)
                            return (
                                value
                                if language == "zh"
                                else (
                                    f"{parsed:%b} {parsed.day}, {parsed.year} ({value})"
                                )
                            )
                        except ValueError:
                            return value

                    def stored_value(row: Memory) -> str:
                        if predicate == "owner" and entity.type == "person":
                            subject = db.get(Entity, row.subject_entity_id)
                            assert subject
                            return subject.canonical_name
                        return str(row.value_json["text"])

                    details = " → ".join(
                        f"{display(stored_value(r))} [{i}]"
                        for i, r in enumerate(rows, 1)
                    )
                    current = (
                        ", ".join(sorted({stored_value(r) for r in active}))
                        or "not established (latest observation revoked or unconfirmed)"
                    )
                    answer = (
                        f"{entity.canonical_name} {predicate}: {details}. "
                        f"Latest recorded {predicate}: {current}."
                    )
                if language == "zh":
                    if not rows:
                        answer = (
                            "没有当前有效且有来源支持的记忆；"
                            "不会恢复已撤销或未经确认的历史事实。"
                        )
                    elif conflicts:
                        answer = "记录存在冲突，需要审核；未选择当前值。" + "; ".join(
                            f"{r.value_json['text']} [{i}]"
                            for i, r in enumerate(rows, 1)
                        )
                    else:
                        label = "负责人" if predicate == "owner" else "截止日期"
                        current_zh = (
                            ", ".join(sorted({stored_value(r) for r in active}))
                            or "未确定（最新记录已撤销或未经确认）"
                        )
                        answer = (
                            f"{entity.canonical_name} {label}：{details}。"
                            f"最新记录的{label}：{current_zh}。"
                        )
                return RecallResult(
                    direct=True,
                    answer=answer,
                    sources=citations,
                    memory_ids=[r.id for r in rows],
                )
            terms = [
                term
                for term in lexical_text(question).split()
                if re.fullmatch(r"\w+", term)
            ][:30]
            if not terms:
                return RecallResult(
                    direct=False, answer=None, sources=[], memory_ids=[]
                )
            tsquery = func.to_tsquery("simple", " | ".join(terms))
            rank = func.ts_rank(Memory.search_tsv, tsquery)
            states = (
                ("active", "superseded", "conflict")
                if re.search(r"history|timeline|历史|变化|过程", query)
                else ("active", "conflict")
            )
            rows = list(
                db.scalars(
                    select(Memory)
                    .where(
                        Memory.user_id == owner,
                        Memory.lifecycle == "recorded",
                        Memory.status.in_(states),
                        Memory.search_tsv.op("@@")(tsquery),
                    )
                    .order_by(rank.desc(), Memory.observed_at.desc())
                    .limit(6)
                )
            )
            optional_sources = [
                self.source(db, row, i) for i, row in enumerate(rows, 1)
            ]
            return RecallResult(
                direct=False,
                answer=None,
                sources=[s for s in optional_sources if s],
                memory_ids=[r.id for r in rows],
            )

    def ingest_chat(self, owner: UUID, assistant_id: UUID) -> None:
        with self.sessions.begin() as db:
            assistant = db.get(Message, assistant_id)
            message = (
                db.get(Message, assistant.reply_to_id)
                if assistant and assistant.user_id == owner and assistant.reply_to_id
                else None
            )
            if (
                not message
                or message.user_id != owner
                or not message.content.casefold().startswith("remember:")
            ):
                return
            value = message.content.partition(":")[2].strip().rstrip(".")
            if not value or len(message.content) > 1800:
                return
            db.scalar(select(User).where(User.id == owner).with_for_update())
            source_key = key_for(message.id, "explicit-chat-v1")
            if db.scalar(
                select(Memory.id).where(
                    Memory.user_id == owner, Memory.source_key == source_key
                )
            ):
                return
            match = re.fullmatch(
                r"([A-Za-z][A-Za-z0-9_-]{1,50}) (owner|deadline) is (.+)",
                value,
                re.IGNORECASE,
            )
            if match:
                subject = self.entity(db, owner, match[1], "project")
                predicate, value = match[2].casefold(), match[3].strip()
                if predicate == "deadline":
                    try:
                        value = date.fromisoformat(value).isoformat()
                    except ValueError:
                        return
            else:
                subject = self.entity(db, owner, "Local user", "person")
                predicate = "fact"
            target = (
                self.entity(db, owner, value, "person")
                if predicate == "owner"
                else None
            )
            payload: dict[str, object] = {"text": value}
            if target:
                payload["object_entity_id"] = str(target.id)
                payload["text"] = target.canonical_name
            row = Memory(
                user_id=owner,
                subject_entity_id=subject.id,
                predicate=predicate,
                slot_key=slot_for(predicate, value),
                value_json=payload,
                memory_type="semantic",
                valid_from=message.created_at,
                source_type="chat",
                source_id=message.id,
                message_id=message.id,
                evidence_quote=message.content,
                line_start=1,
                line_end=1,
                confidence=1,
                evidence_kind="explicit_fact",
                review_state="confirmed",
                status="active",
                source_key=source_key,
                search_text="",
            )
            db.add(row)
            db.flush()
            if target:
                db.add(
                    EntityRelation(
                        user_id=owner,
                        from_entity_id=subject.id,
                        to_entity_id=target.id,
                        relation=predicate,
                        memory_id=row.id,
                    )
                )
            self.recompute(db, owner, subject.id, row.slot_key)
            self.refresh_search(db, owner)
            audit(
                db,
                owner,
                "chat_memory_recorded",
                "memory",
                row.id,
                message_id=str(message.id),
            )
