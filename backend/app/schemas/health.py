from typing import Literal

from pydantic import BaseModel, Field


class Dependencies(BaseModel):
    postgres: Literal["ready", "unavailable"]
    pgvector: Literal["ready", "unavailable"]
    schema_status: Literal["ready", "unavailable"] = Field(alias="schema")
    redis: Literal["ready", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["memora-api"] = "memora-api"
    version: Literal["0.1.0"] = "0.1.0"
    dependencies: Dependencies


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, object] | None = None
