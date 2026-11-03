from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID | None = None
    request_id: UUID = Field(default_factory=uuid4)
    message: str = Field(min_length=1, max_length=4000)
    attachments: list[UUID] = Field(default_factory=list, max_length=5)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID = Field(default_factory=uuid4)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    last_message_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    position: int
    role: Literal["user", "assistant"]
    content: str
    status: Literal[
        "complete", "streaming", "failed", "cancelled", "interrupted", "incomplete"
    ]
    error_code: str | None
    reply_to_id: UUID | None
    citations_json: list[dict[str, object]]
    tool_calls_json: list[dict[str, object]]
    document_ids: list[str]
    created_at: datetime
    updated_at: datetime


class ChatConfiguration(BaseModel):
    configured: bool
    missing: list[str]
    provider: str
    model: str
    message: str


class StreamEvent(BaseModel):
    event: Literal[
        "message_start",
        "token",
        "tool_start",
        "tool_result",
        "citation",
        "message_end",
        "error",
    ]
    conversation_id: UUID
    message_id: UUID
    text: str | None = None
    status: str | None = None
    code: str | None = None
    message: str | None = None
    request_id: str | None = None
    source: dict[str, object] | None = None
