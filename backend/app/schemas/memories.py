from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.documents import SourceCitation


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class EntityOut(Strict):
    id: UUID
    type: str
    canonical_name: str
    revision: int
    aliases: list[str]
    merged_into_id: UUID | None


class AliasRequest(Strict):
    revision: int = Field(ge=1)
    alias: str = Field(min_length=1, max_length=180)
    confirm_identity: Literal[True]


class MergeRequest(Strict):
    revision: int = Field(ge=1)
    target_id: UUID
    confirm_identity: Literal[True]


class MemoryOut(Strict):
    id: UUID
    subject_entity_id: UUID
    subject_name: str = ""
    predicate: str
    value_json: dict[str, object]
    memory_type: str
    valid_from: datetime | None
    valid_to: datetime | None
    observed_at: datetime
    source_type: str
    source_id: UUID
    meeting_id: UUID | None
    message_id: UUID | None
    evidence_quote: str
    line_start: int | None
    line_end: int | None
    confidence: float
    evidence_kind: str
    status: str
    lifecycle: str
    revision: int
    supersedes_id: UUID | None
    correction_reason: str | None
    source: SourceCitation | None = None


class Correction(Strict):
    revision: int = Field(ge=1)
    value: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=1000)
    valid_from: datetime | None = None
    subject_entity_id: UUID | None = None

    @field_validator("valid_from")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("UTC offset required")
        return value


class ImportResult(Strict):
    processed: int
    inserted: int
    next_cursor: UUID | None = None


class RecallRequest(Strict):
    question: str = Field(min_length=1, max_length=2000)


class RecallResult(Strict):
    direct: bool
    answer: str | None
    sources: list[SourceCitation]
    memory_ids: list[UUID]
