import hashlib
import math
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4, uuid5

from redis import Redis
from rq import Queue
from rq.job import Callback
from rq.serializers import JSONSerializer
from sqlalchemy import Engine, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Document, DocumentChunk, Job, User
from app.db.session import session_factory
from app.schemas.documents import DocumentOut, JobOut, SourceCitation, UploadResult
from app.services.embedding import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    embedding_configuration,
    profile,
)
from app.services.llm.provider import ChatError
from app.services.pdf import chunk_pages, extract_pages, lexical_text
from app.services.storage import PrivateStorage, safe_filename

ACTIVE = ("queued", "processing", "embedding")


class DocumentService:
    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self.settings = settings
        self.sessions = session_factory(engine)
        self.storage = PrivateStorage(settings.storage_root)
        self.embeddings = embeddings or OpenAIEmbeddingProvider(settings)
        self.redis = Redis.from_url(
            settings.redis_url.get_secret_value(),
            socket_connect_timeout=settings.dependency_timeout_seconds,
            socket_timeout=settings.dependency_timeout_seconds,
        )

    def owned(
        self, db: Session, owner: UUID, identifier: UUID, lock: bool = False
    ) -> Document:
        query = select(Document).where(
            Document.id == identifier, Document.user_id == owner
        )
        row = db.scalar(query.with_for_update() if lock else query)
        if row is None:
            raise ChatError("NOT_FOUND", "Document not found.", 404)
        return row

    def out(self, row: Document) -> DocumentOut:
        result = DocumentOut.model_validate(row)
        if result.status == "ready" and row.embedding_profile != profile(self.settings):
            result.status = "needs_reindex"
            result.error_code = "INDEX_PROFILE_MISMATCH"
            result.error_message = "Embedding settings changed. Rebuild this index."
        return result

    def listing(self, owner: UUID) -> list[DocumentOut]:
        with self.sessions() as db:
            return [
                self.out(row)
                for row in db.scalars(
                    select(Document)
                    .where(Document.user_id == owner)
                    .order_by(Document.created_at.desc())
                )
            ]

    def detail(self, owner: UUID, identifier: UUID) -> DocumentOut:
        with self.sessions() as db:
            return self.out(self.owned(db, owner, identifier))

    def enqueue(self, identifier: UUID) -> None:
        try:
            queue = Queue("documents", connection=self.redis, serializer=JSONSerializer)
            queue.enqueue(
                "app.workers.ingest.ingest_document",
                str(identifier),
                job_id=str(identifier),
                job_timeout=self.settings.ingest_job_timeout_seconds,
                result_ttl=3600,
                failure_ttl=86400,
                on_failure=Callback("app.workers.ingest.failed_job"),
            )
        except Exception:
            self.fail(
                identifier,
                "QUEUE_UNAVAILABLE",
                "Could not enqueue ingestion. Check Redis and retry explicitly.",
            )

    def upload(
        self, owner: UUID, filename: str, mime: str, data: bytes
    ) -> UploadResult:
        if (
            not filename.lower().endswith(".pdf")
            or mime.split(";")[0].lower() != "application/pdf"
        ):
            raise ChatError(
                "PDF_TYPE_REQUIRED",
                "Only application/pdf files with .pdf extension are supported.",
                415,
            )
        if not data or len(data) > self.settings.pdf_max_upload_bytes:
            raise ChatError(
                "PDF_SIZE_LIMIT", "PDF is empty or exceeds the upload limit.", 413
            )
        if not data.startswith(b"%PDF-"):
            raise ChatError("PDF_INVALID_HEADER", "File content is not a PDF.", 422)
        checksum = hashlib.sha256(data).hexdigest()
        key: str | None = None
        try:
            with self.sessions.begin() as db:
                db.execute(
                    insert(User)
                    .values(
                        id=owner,
                        email=f"{owner}@demo.invalid",
                        display_name="Local demo",
                        auth_method="demo",
                    )
                    .on_conflict_do_nothing()
                )
                db.scalar(select(User).where(User.id == owner).with_for_update())
                previous = db.scalar(
                    select(Document).where(
                        Document.user_id == owner,
                        Document.checksum == checksum,
                        Document.kind == "PDF",
                    )
                )
                if previous:
                    assert previous.current_job_id is not None
                    return UploadResult(
                        document_id=previous.id,
                        job_id=previous.current_job_id,
                        duplicate=True,
                    )
                self.admit(db, owner)
                doc_id, job_id = uuid4(), uuid4()
                key = f"{owner}/{doc_id}.pdf"
                self.storage.write(key, data)
                doc = Document(
                    id=doc_id,
                    user_id=owner,
                    kind="PDF",
                    filename=safe_filename(filename),
                    checksum=checksum,
                    storage_key=key,
                    status="queued",
                    current_job_id=job_id,
                )
                db.add(doc)
                db.flush()
                db.add(
                    Job(
                        id=job_id,
                        owner_id=owner,
                        target_id=doc_id,
                        embedding_profile=profile(self.settings),
                    )
                )
            self.enqueue(job_id)
            return UploadResult(document_id=doc_id, job_id=job_id)
        except Exception:
            if key:
                self.storage.delete(key)
            raise

    def admit(self, db: Session, owner: UUID) -> None:
        active = (
            db.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.owner_id == owner, Job.status.in_(("queued", "running")))
            )
            or 0
        )
        if active >= self.settings.ingest_max_active_jobs:
            raise ChatError(
                "INGEST_LIMIT_REACHED",
                "Too many active document jobs. Wait or recover a failed job first.",
                429,
            )

    def reprocess(
        self, owner: UUID, identifier: UUID, reindex: bool, reparse: bool
    ) -> UploadResult:
        with self.sessions.begin() as db:
            db.scalar(select(User).where(User.id == owner).with_for_update())
            row = self.owned(db, owner, identifier, lock=True)
            if row.status in ACTIVE:
                assert row.current_job_id is not None
                return UploadResult(
                    document_id=row.id, job_id=row.current_job_id, duplicate=True
                )
            if row.status == "ready" and not reindex:
                if row.embedding_profile != profile(self.settings):
                    raise ChatError(
                        "INDEX_PROFILE_MISMATCH",
                        "Use explicit reindex after changing model or dimensions.",
                        409,
                    )
                assert row.current_job_id is not None
                return UploadResult(
                    document_id=row.id, job_id=row.current_job_id, duplicate=True
                )
            self.admit(db, owner)
            job_id = uuid4()
            row.status, row.current_job_id = "queued", job_id
            row.error_code = row.error_message = None
            if reparse:
                db.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_id == row.id)
                )
                row.extracted, row.page_count, row.chunk_count = False, 0, 0
            else:
                db.execute(
                    update(DocumentChunk)
                    .where(DocumentChunk.document_id == row.id)
                    .values(
                        embedding=None, embedding_profile="", embedding_dimensions=0
                    )
                )
            db.add(
                Job(
                    id=job_id,
                    owner_id=owner,
                    target_id=row.id,
                    reparse=reparse,
                    embedding_profile=profile(self.settings),
                )
            )
        self.enqueue(job_id)
        return UploadResult(document_id=identifier, job_id=job_id)

    def job(self, owner: UUID, identifier: UUID) -> JobOut:
        with self.sessions() as db:
            row = db.scalar(
                select(Job).where(Job.id == identifier, Job.owner_id == owner)
            )
            if row is None:
                raise ChatError("NOT_FOUND", "Job not found.", 404)
            stale = datetime.now(UTC) - timedelta(
                seconds=self.settings.ingest_job_timeout_seconds + 60
            )
            if row.status in ("queued", "running") and row.updated_at < stale:
                self.fail(
                    identifier,
                    "JOB_INTERRUPTED",
                    "Worker did not finish within the job deadline. Retry explicitly.",
                )
                db.refresh(row)
            return JobOut.model_validate(row)

    def fail(self, identifier: UUID, code: str, message: str) -> None:
        with self.sessions.begin() as db:
            job = db.get(Job, identifier, with_for_update=True)
            if job is None or job.status not in ("queued", "running"):
                return
            job.status, job.error_code, job.error_message = "failed", code, message
            document = db.get(Document, job.target_id)
            if document and document.current_job_id == identifier:
                document.status, document.error_code, document.error_message = (
                    "failed",
                    code,
                    message,
                )

    def ingest(self, identifier: UUID) -> None:
        try:
            with self.sessions.begin() as db:
                job = db.get(Job, identifier, with_for_update=True)
                if job is None or job.status != "queued":
                    return
                doc = db.get(Document, job.target_id)
                if doc is None or doc.current_job_id != identifier:
                    return
                if job.embedding_profile != profile(self.settings):
                    raise ChatError(
                        "WORKER_CONFIG_MISMATCH",
                        "API/worker embedding settings differ. Restart both.",
                    )
                job.status, job.stage, job.attempts = (
                    "running",
                    "extracting",
                    job.attempts + 1,
                )
                doc.status = "processing"
                key, cached, owner, doc_id, checksum = (
                    doc.storage_key,
                    doc.extracted,
                    doc.user_id,
                    doc.id,
                    doc.checksum,
                )
            if not cached:
                path = self.storage.path(key)
                if (
                    path.stat().st_size > self.settings.pdf_max_upload_bytes
                    or hashlib.sha256(path.read_bytes()).hexdigest() != checksum
                ):
                    raise ChatError(
                        "PDF_STORAGE_INTEGRITY",
                        "Stored PDF no longer matches its upload checksum.",
                    )
                pages = extract_pages(path, self.settings)
                pieces = chunk_pages(
                    pages,
                    self.settings.pdf_chunk_tokens,
                    self.settings.pdf_chunk_overlap,
                    self.settings.pdf_max_chunks,
                )
                with self.sessions.begin() as db:
                    current_job = db.get(Job, identifier, with_for_update=True)
                    doc = db.get(Document, doc_id, with_for_update=True)
                    if (
                        current_job is None
                        or current_job.status != "running"
                        or doc is None
                        or doc.current_job_id != identifier
                    ):
                        return
                    db.execute(
                        delete(DocumentChunk).where(DocumentChunk.document_id == doc_id)
                    )
                    for piece in pieces:
                        db.add(
                            DocumentChunk(
                                id=uuid5(
                                    doc_id, f"{piece.chunk_index}:{piece.text_hash}"
                                ),
                                user_id=owner,
                                document_id=doc_id,
                                chunk_index=piece.chunk_index,
                                text=piece.text,
                                page_no=piece.page_no,
                                token_count=piece.token_count,
                                text_hash=piece.text_hash,
                                search_text=lexical_text(piece.text),
                            )
                        )
                    doc.extracted, doc.page_count, doc.chunk_count = (
                        True,
                        len(pages),
                        len(pieces),
                    )
            with self.sessions.begin() as db:
                job = db.get(Job, identifier, with_for_update=True)
                doc = db.get(Document, doc_id)
                if (
                    job is None
                    or job.status != "running"
                    or doc is None
                    or doc.current_job_id != identifier
                ):
                    return
                job.stage, job.progress, doc.status = "embedding", 40, "embedding"
                chunks = list(
                    db.scalars(
                        select(DocumentChunk)
                        .where(DocumentChunk.document_id == doc_id)
                        .order_by(DocumentChunk.chunk_index)
                    )
                )
                texts = [chunk.text for chunk in chunks]
                chunk_ids = [chunk.id for chunk in chunks]
            if not texts:
                raise ChatError("PDF_EMPTY", "PDF produced no indexable chunks.")
            vectors = []
            batch = self.settings.embedding_batch_size
            for start in range(0, len(texts), batch):
                vectors.extend(self.embeddings.embed(texts[start : start + batch]))
                with self.sessions.begin() as db:
                    db.execute(
                        update(Job)
                        .where(Job.id == identifier, Job.status == "running")
                        .values(
                            progress=40
                            + int(50 * min(start + batch, len(texts)) / len(texts))
                        )
                    )
            if len(vectors) != len(chunk_ids) or any(
                len(vector) != self.settings.embedding_dimensions
                or not all(math.isfinite(value) for value in vector)
                or sum(value * value for value in vector) <= 1e-12
                for vector in vectors
            ):
                raise ChatError(
                    "EMBEDDING_INVALID_RESPONSE",
                    "Embedding vectors failed count/dimension/norm validation.",
                )
            with self.sessions.begin() as db:
                job = db.get(Job, identifier, with_for_update=True)
                doc = db.get(Document, doc_id, with_for_update=True)
                if (
                    doc is None
                    or job is None
                    or doc.current_job_id != identifier
                    or job.status != "running"
                ):
                    return
                for chunk_id, vector in zip(chunk_ids, vectors, strict=True):
                    db.execute(
                        update(DocumentChunk)
                        .where(DocumentChunk.id == chunk_id)
                        .values(
                            embedding=vector,
                            embedding_profile=profile(self.settings),
                            embedding_dimensions=self.settings.embedding_dimensions,
                        )
                    )
                doc.status, doc.embedding_profile = "ready", profile(self.settings)
                doc.embedding_model, doc.embedding_dimensions = (
                    self.settings.embedding_model,
                    self.settings.embedding_dimensions,
                )
                doc.error_code = doc.error_message = None
                job.status, job.stage, job.progress = "succeeded", "complete", 100
        except Exception as exc:
            error = (
                exc
                if isinstance(exc, ChatError)
                else ChatError(
                    "INGEST_FAILED",
                    "Processing failed. Check storage/dependencies and retry.",
                )
            )
            self.fail(identifier, error.code, error.message)

    def validate_scope(self, owner: UUID, identifiers: list[UUID]) -> None:
        with self.sessions() as db:
            for identifier in set(identifiers):
                row = self.owned(db, owner, identifier)
                if row.status != "ready":
                    raise ChatError(
                        "DOCUMENT_NOT_READY",
                        "Selected PDF is not ready. Inspect processing status first.",
                        409,
                    )
                if row.embedding_profile != profile(self.settings):
                    raise ChatError(
                        "INDEX_PROFILE_MISMATCH",
                        "Selected PDF requires explicit reindexing for this profile.",
                        409,
                    )

    def retrieve(
        self, owner: UUID, question: str, identifiers: list[UUID]
    ) -> list[SourceCitation]:
        config = embedding_configuration(self.settings)
        if not config.configured:
            raise ChatError("EMBEDDING_NOT_CONFIGURED", config.message, 503)
        with self.sessions() as db:
            if not identifiers:
                identifiers = list(
                    db.scalars(
                        select(Document.id).where(
                            Document.user_id == owner, Document.status == "ready"
                        )
                    )
                )
        if not identifiers:
            return []
        self.validate_scope(owner, identifiers)
        vector = self.embeddings.embed([question])[0]
        distance = DocumentChunk.embedding.cosine_distance(vector)
        terms = [
            word
            for word in lexical_text(question).split()
            if word.isalnum()
            and word not in {"what", "when", "is", "the", "a", "of", "in", "to", "does"}
        ]
        tsquery = func.to_tsquery("simple", " | ".join(terms) or "unlikelyemptyquery")
        rank = func.ts_rank_cd(DocumentChunk.search_tsv, tsquery)
        with self.sessions() as db:
            base = (
                select(DocumentChunk, Document.filename)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.user_id == owner,
                    Document.user_id == owner,
                    Document.id.in_(identifiers),
                    Document.status == "ready",
                    Document.embedding_profile == profile(self.settings),
                    DocumentChunk.embedding_profile == profile(self.settings),
                    DocumentChunk.embedding_dimensions
                    == self.settings.embedding_dimensions,
                    DocumentChunk.embedding.is_not(None),
                )
            )
            limit = self.settings.rag_top_k * 4
            vector_rows = db.execute(
                base.add_columns(distance.label("metric"))
                .where(distance <= 1 - self.settings.rag_min_similarity)
                .order_by(distance, DocumentChunk.id)
                .limit(limit)
            ).all()
            text_rows = db.execute(
                base.add_columns(rank.label("metric"))
                .where(DocumentChunk.search_tsv.op("@@")(tsquery))
                .order_by(rank.desc(), DocumentChunk.id)
                .limit(limit)
            ).all()
            candidates: dict[UUID, SourceCitation] = {}
            for kind, rows in (("vector", vector_rows), ("text", text_rows)):
                for position, row in enumerate(rows, 1):
                    chunk, filename = cast(DocumentChunk, row[0]), str(row[1])
                    if chunk.id not in candidates:
                        relevant = [
                            chunk.text.lower().find(term)
                            for term in sorted(terms, key=len, reverse=True)
                            if term in chunk.text.lower()
                        ]
                        offset = max(0, (relevant[0] if relevant else 0) - 200)
                        excerpt = (
                            chunk.text[offset:]
                            .encode()[:1400]
                            .decode("utf-8", errors="ignore")
                        )
                        candidates[chunk.id] = SourceCitation(
                            key="pdf:" + str(chunk.id),
                            label=0,
                            chunk_id=chunk.id,
                            document_id=chunk.document_id,
                            filename=filename,
                            page_no=chunk.page_no,
                            excerpt=excerpt,
                            score=0,
                        )
                    source = candidates[chunk.id]
                    source.score += 1 / (60 + position)
                    if kind == "vector":
                        source.vector_rank = position
                    else:
                        source.text_rank = position
            sources = sorted(
                candidates.values(),
                key=lambda item: (
                    -item.score,
                    item.text_rank or 100000,
                    item.vector_rank or 100000,
                    str(item.chunk_id),
                ),
            )[: self.settings.rag_top_k]
            for label, source in enumerate(sources, 1):
                source.label = label
            return sources

    def remove(self, owner: UUID, identifier: UUID) -> None:
        with self.sessions.begin() as db:
            row = self.owned(db, owner, identifier, lock=True)
            key = row.storage_key
            # Remove original first; a storage failure must not claim deletion success.
            self.storage.delete(key)
            db.delete(row)
