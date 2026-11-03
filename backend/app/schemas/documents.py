from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str
    kind: str
    status: str
    page_count: int
    chunk_count: int
    extracted: bool
    error_code: str | None
    error_message: str | None
    embedding_model: str
    embedding_dimensions: int
    current_job_id: UUID | None
    created_at: datetime
    updated_at: datetime


class UploadResult(BaseModel):
    document_id: UUID
    job_id: UUID
    duplicate: bool = False


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    target_id: UUID
    status: str
    stage: str
    progress: int
    attempts: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentConfiguration(BaseModel):
    configured: bool
    missing: list[str]
    model: str
    dimensions: int
    profile: str
    max_upload_bytes: int
    message: str


class SourceCitation(BaseModel):
    key: str
    label: int
    chunk_id: UUID
    document_id: UUID
    filename: str
    page_no: int
    excerpt: str
    source_type: str = "internal_document"
    score: float
    vector_rank: int | None = None
    text_rank: int | None = None


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[UUID] = Field(default_factory=list, max_length=5)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be blank")
        return value.strip()


class SearchResult(BaseModel):
    sources: list[SourceCitation]
    message: str


class ReprocessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reparse: bool = False
