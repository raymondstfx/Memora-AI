from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.documents import JobOut

TaskStatus = Literal["proposed", "open", "in_progress", "done", "cancelled"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Evidence(Strict):
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=1800)
    kind: Literal["explicit_fact", "inference", "unknown"]


class Person(Strict):
    name: str = Field(min_length=1, max_length=150)
    role: str | None = Field(default=None, max_length=150)
    evidence: Evidence


class Claim(Strict):
    text: str = Field(min_length=1, max_length=1500)
    evidence: Evidence


class RiskExtract(Strict):
    type: Literal[
        "schedule", "dependency", "resourcing", "decision", "quality", "compliance"
    ]
    title: str = Field(min_length=1, max_length=300)
    severity: Literal["high", "medium", "low"]
    rationale: str = Field(min_length=1, max_length=1500)
    mitigation: str = Field(min_length=1, max_length=1500)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    evidence: Evidence


class TaskExtract(Strict):
    title: str = Field(min_length=1, max_length=300)
    owner_name: str | None = Field(default=None, max_length=150)
    due_text: str | None = Field(default=None, max_length=200)
    risk_index: int | None = Field(default=None, ge=0)
    evidence: Evidence


class MemoryClaim(Strict):
    subject: str = Field(min_length=1, max_length=180)
    subject_type: Literal["person", "project", "place", "topic"]
    predicate: Literal["owner", "deadline", "role", "location", "fact"]
    value: str = Field(min_length=1, max_length=2000)
    evidence: Evidence


class MeetingExtraction(Strict):
    summary: str = Field(min_length=1, max_length=3000)
    topics: list[str] = Field(default_factory=list, max_length=12)
    people: list[Person] = Field(default_factory=list, max_length=30)
    decisions: list[Claim] = Field(default_factory=list, max_length=30)
    risks: list[RiskExtract] = Field(default_factory=list, max_length=20)
    tasks: list[TaskExtract] = Field(default_factory=list, max_length=30)
    candidate_facts: list[Claim] = Field(default_factory=list, max_length=40)
    memory_claims: list[MemoryClaim] = Field(default_factory=list, max_length=40)


class TaskOut(Strict):
    id: UUID
    meeting_id: UUID
    risk_id: UUID | None
    title: str
    owner_name: str | None
    due_at: datetime | None
    due_text: str | None
    status: str
    needs_review: bool
    evidence_json: Evidence
    updated_at: datetime


class TaskPatch(Strict):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    owner_name: str | None = Field(default=None, max_length=150)
    due_at: datetime | None = None
    status: TaskStatus | None = None

    @model_validator(mode="after")
    def nonempty(self) -> "TaskPatch":
        if not self.model_fields_set or any(
            getattr(self, key) is None
            for key in self.model_fields_set & {"title", "status"}
        ):
            raise ValueError("Provide fields to edit; title/status cannot be null")
        return self

    @field_validator("due_at")
    @classmethod
    def aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("UTC offset required")
        return v


class RiskOut(Strict):
    id: UUID
    type: str
    title: str
    severity: str
    rationale: str
    mitigation: str
    confidence: float
    status: str
    evidence_json: Evidence


class EmailOut(Strict):
    id: UUID
    meeting_id: UUID
    risk_id: UUID
    recipients_json: list[str]
    subject: str
    body: str
    revision: int
    approval_status: str
    send_status: str
    error_code: str | None
    provider_message_id: str | None
    sent_at: datetime | None


def validate_address(value: str) -> str:
    import re

    if not re.fullmatch(
        (
            "[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za"
            "-z0-9.-]*[A-Za-z0-9])?\\.[A-Za-z]{2,63}"
        ),
        value,
    ):
        raise ValueError("Use an explicit email address without display names")
    return value.lower()


class EmailPatch(Strict):
    revision: int = Field(ge=1)
    recipients: list[str] | None = Field(default=None, max_length=5)
    subject: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, min_length=1, max_length=12000)

    @model_validator(mode="after")
    def nonempty(self) -> "EmailPatch":
        edits = self.model_fields_set - {"revision"}
        if not edits or any(getattr(self, key) is None for key in edits):
            raise ValueError("Provide non-null draft fields to edit")
        return self

    @field_validator("recipients")
    @classmethod
    def addresses(cls, v: list[str] | None) -> list[str] | None:
        return (
            sorted(set(validate_address(x.strip()) for x in v))
            if v is not None
            else None
        )

    @field_validator("subject")
    @classmethod
    def header(cls, v: str | None) -> str | None:
        if v is not None and ("\r" in v or "\n" in v):
            raise ValueError("Header newline is forbidden")
        return v


class Approval(Strict):
    revision: int = Field(ge=1)
    idempotency_key: UUID
    confirm_send: Literal[True]


class MeetingOut(Strict):
    id: UUID
    document_id: UUID
    title: str
    occurred_at: datetime | None
    date_precision: str
    timezone: str | None
    location: str | None
    analysis_status: str
    summary: str


class MeetingUpload(Strict):
    meeting_id: UUID
    job_id: UUID
    duplicate: bool


class AnalysisOut(Strict):
    meeting: MeetingOut
    analysis: MeetingExtraction | None
    risks: list[RiskOut]
    tasks: list[TaskOut]
    emails: list[EmailOut]
    error_code: str | None
    error_message: str | None
    needs_review: bool
    job: JobOut | None


class TranscriptLine(Strict):
    number: int
    text: str
    speaker: str | None


class AuditOut(Strict):
    id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    metadata_json: dict[str, object]
    created_at: datetime
