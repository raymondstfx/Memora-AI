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
