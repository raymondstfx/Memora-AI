from datetime import datetime
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.auth import get_current_user
from app.schemas.health import ErrorResponse
from app.schemas.memories import (
    AliasRequest,
    Correction,
    EntityOut,
    ImportResult,
    MemoryOut,
    MergeRequest,
    RecallRequest,
    RecallResult,
)
from app.services.llm.provider import ChatError
from app.services.memories import MemoryService

router = APIRouter(
    prefix="/api",
    tags=["memories"],
    responses={code: {"model": ErrorResponse} for code in (404, 409, 422, 503)},
)
Owner = Annotated[UUID, Depends(get_current_user)]


def service(request: Request) -> MemoryService:
    return cast(MemoryService, request.app.state.memories)


@router.get("/entities", response_model=list[EntityOut])
def entities(request: Request, owner: Owner) -> list[EntityOut]:
    return service(request).entities(owner)


@router.post("/entities/{identifier}/aliases", response_model=EntityOut)
def alias(
    identifier: UUID, body: AliasRequest, request: Request, owner: Owner
) -> EntityOut:
    return service(request).alias(owner, identifier, body)


@router.post("/entities/{identifier}/merge", response_model=EntityOut)
def merge(
    identifier: UUID, body: MergeRequest, request: Request, owner: Owner
) -> EntityOut:
    return service(request).merge(owner, identifier, body)


@router.get("/memories", response_model=list[MemoryOut])
def listing(
    request: Request,
    owner: Owner,
    entity_id: UUID | None = None,
    status: str | None = None,
    memory_type: str | None = None,
    valid_at: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> list[MemoryOut]:
    if valid_at is not None and valid_at.tzinfo is None:
        raise ChatError("UTC_OFFSET_REQUIRED", "valid_at requires a UTC offset.", 422)
    return service(request).listing(
        owner, entity_id, status, memory_type, valid_at, limit
    )


@router.post("/memories/import-meetings", response_model=ImportResult)
def import_meetings(
    request: Request, owner: Owner, after: UUID | None = None
) -> ImportResult:
    return service(request).import_meetings(owner, after)


@router.post("/memories/search", response_model=RecallResult)
def search(body: RecallRequest, request: Request, owner: Owner) -> RecallResult:
    return service(request).recall(owner, body.question)


@router.get("/memories/{identifier}", response_model=MemoryOut)
def memory(identifier: UUID, request: Request, owner: Owner) -> MemoryOut:
    memories = service(request)
    with memories.sessions() as db:
        return memories.out(db, memories.owned(db, owner, identifier))


@router.patch("/memories/{identifier}", response_model=MemoryOut)
def correct(
    identifier: UUID, body: Correction, request: Request, owner: Owner
) -> MemoryOut:
    return service(request).correct(owner, identifier, body)


@router.delete("/memories/{identifier}", status_code=204)
def revoke(
    identifier: UUID,
    request: Request,
    owner: Owner,
    revision: Annotated[int, Query(ge=1)],
) -> Response:
    service(request).revoke(owner, identifier, revision)
    return Response(status_code=204)
