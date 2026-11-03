from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SystemMetadata(Base):
    """Infrastructure only; user-owned feature tables are added in later phases."""

    __tablename__ = "system_metadata"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Timestamps, Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    auth_method: Mapped[str] = mapped_column(String(30), default="demo")


class Conversation(Timestamps, Base):
    __tablename__ = "conversations"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_position: Mapped[int] = mapped_column(Integer, default=0)
    next_position: Mapped[int] = mapped_column(Integer, default=1)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Message(Timestamps, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "position", name="uq_message_position"),
        UniqueConstraint("user_id", "client_request_id", name="uq_message_request"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),
        CheckConstraint(
            "status IN ('complete', 'streaming', 'failed', 'cancelled', "
            "'interrupted', 'incomplete')",
            name="ck_message_status",
        ),
        Index(
            "uq_conversation_stream",
            "conversation_id",
            unique=True,
            postgresql_where=text("status = 'streaming'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    client_request_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    reply_to_id: Mapped[UUID | None] = mapped_column(ForeignKey("messages.id"))
    citations_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    tool_calls_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    document_ids: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default="[]"
    )


class Document(Timestamps, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("user_id", "checksum", "kind", name="uq_document_checksum"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="PDF")
    filename: Mapped[str] = mapped_column(String(180))
    checksum: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    extracted: Mapped[bool] = mapped_column(default=False)
    embedding_profile: Mapped[str] = mapped_column(String(64), default="")
    embedding_model: Mapped[str] = mapped_column(String(200), default="")
    embedding_dimensions: Mapped[int] = mapped_column(Integer, default=0)
    current_job_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class DocumentChunk(Timestamps, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_index"),
        Index("ix_chunks_search", "search_tsv", postgresql_using="gin"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    page_no: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[int] = mapped_column(Integer)
    text_hash: Mapped[str] = mapped_column(String(64))
    search_text: Mapped[str] = mapped_column(Text)
    search_tsv: Mapped[object] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', search_text)", persisted=True)
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(), nullable=True)
    embedding_profile: Mapped[str] = mapped_column(String(64), default="", index=True)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, default=0)


class Job(Timestamps, Base):
    __tablename__ = "jobs"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    target_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    job_type: Mapped[str] = mapped_column(String(30), default="pdf_ingest")
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(30), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_profile: Mapped[str] = mapped_column(String(64))
    reparse: Mapped[bool] = mapped_column(default=False)


class Meeting(Timestamps, Base):
    __tablename__ = "meetings"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    analysis_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    analysis_status: Mapped[str] = mapped_column(String(30), default="queued")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    @property
    def date_precision(self) -> str:
        return str(self.metadata_json.get("date_precision", "unknown"))


class Decision(Timestamps, Base):
    __tablename__ = "decisions"
    __table_args__ = (UniqueConstraint("meeting_id", "dedupe_key"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSON)
    dedupe_key: Mapped[str] = mapped_column(String(64))


class Risk(Timestamps, Base):
    __tablename__ = "risks"
    __table_args__ = (UniqueConstraint("meeting_id", "dedupe_key"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(20))
    rationale: Mapped[str] = mapped_column(Text)
    mitigation: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column(String(30), default="needs_review")
    dedupe_key: Mapped[str] = mapped_column(String(64))


class Task(Timestamps, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key"),
        CheckConstraint(
            "status IN ('proposed','open','in_progress','done','cancelled')",
            name="ck_task_status",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), index=True)
    risk_id: Mapped[UUID | None] = mapped_column(ForeignKey("risks.id"))
    title: Mapped[str] = mapped_column(String(300))
    owner_name: Mapped[str | None] = mapped_column(String(150))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    due_text: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="proposed", index=True)
    needs_review: Mapped[bool] = mapped_column(default=True)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSON)
    dedupe_key: Mapped[str] = mapped_column(String(64))


class EmailOutbox(Timestamps, Base):
    __tablename__ = "email_outbox"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), index=True)
    risk_id: Mapped[UUID] = mapped_column(ForeignKey("risks.id"), unique=True)
    recipients_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    approval_status: Mapped[str] = mapped_column(String(30), default="draft")
    send_status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    idempotency_key: Mapped[UUID | None] = mapped_column(Uuid)
    approved_revision: Mapped[int | None] = mapped_column(Integer)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    error_code: Mapped[str | None] = mapped_column(String(60))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    resource_type: Mapped[str] = mapped_column(String(30))
    resource_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EmailApproval(Base):
    __tablename__ = "email_approvals"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    email_id: Mapped[UUID] = mapped_column(ForeignKey("email_outbox.id"), index=True)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid)
    revision: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Entity(Timestamps, Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("user_id", "type", "normalized_name"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    canonical_name: Mapped[str] = mapped_column(String(180))
    normalized_name: Mapped[str] = mapped_column(String(180))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    merged_into_id: Mapped[UUID | None] = mapped_column(ForeignKey("entities.id"))


class EntityAlias(Timestamps, Base):
    __tablename__ = "entity_aliases"
    __table_args__ = (UniqueConstraint("user_id", "type", "normalized_name"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(180))
    normalized_name: Mapped[str] = mapped_column(String(180))
    confirmed_by_user: Mapped[bool] = mapped_column(default=False)


class Memory(Timestamps, Base):
    __tablename__ = "memories"
    __table_args__ = (
        UniqueConstraint("user_id", "source_key"),
        Index("ix_memory_search", "search_tsv", postgresql_using="gin"),
        Index(
            "ix_memory_slot_time",
            "user_id",
            "subject_entity_id",
            "slot_key",
            "valid_from",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    subject_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id"), index=True
    )
    predicate: Mapped[str] = mapped_column(String(50))
    slot_key: Mapped[str] = mapped_column(String(120))
    value_json: Mapped[dict[str, object]] = mapped_column(JSON)
    memory_type: Mapped[str] = mapped_column(String(30))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    meeting_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meetings.id"), index=True
    )
    message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id"), index=True
    )
    evidence_quote: Mapped[str] = mapped_column(Text)
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column()
    evidence_kind: Mapped[str] = mapped_column(String(30))
    lifecycle: Mapped[str] = mapped_column(String(30), default="recorded")
    review_state: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_id: Mapped[UUID | None] = mapped_column(ForeignKey("memories.id"))
    correction_reason: Mapped[str | None] = mapped_column(Text)
    source_key: Mapped[str] = mapped_column(String(64))
    search_text: Mapped[str] = mapped_column(Text)
    search_tsv: Mapped[object] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', search_text)", persisted=True)
    )


class EntityRelation(Timestamps, Base):
    __tablename__ = "entity_relations"
    __table_args__ = (UniqueConstraint("memory_id", "relation"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    from_entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), index=True)
    to_entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), index=True)
    relation: Mapped[str] = mapped_column(String(50))
    memory_id: Mapped[UUID] = mapped_column(ForeignKey("memories.id"), index=True)


class Presentation(Timestamps, Base):
    __tablename__ = "presentations"
    __table_args__ = (UniqueConstraint("user_id", "request_key"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    request_key: Mapped[UUID] = mapped_column(Uuid)
    request_json: Mapped[dict[str, object]] = mapped_column(JSON)
    outline_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    sources_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    stage: Mapped[str] = mapped_column(String(30), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(60))
    page_count: Mapped[int | None] = mapped_column(Integer)
