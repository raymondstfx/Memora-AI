from datetime import datetime
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core.auth import get_current_user
from app.db.models import EmailOutbox
from app.schemas.health import ErrorResponse
from app.schemas.meetings import (
    AnalysisOut,
    Approval,
    AuditOut,
    EmailOut,
    EmailPatch,
    MeetingOut,
    MeetingUpload,
    TaskOut,
    TaskPatch,
    TranscriptLine,
)
from app.services.emails import EmailService
from app.services.llm.provider import ChatError
from app.services.meetings import MeetingService

router = APIRouter(
    prefix="/api",
    tags=["meetings-actions"],
    responses={
        code: {"model": ErrorResponse} for code in (404, 409, 413, 415, 422, 429, 503)
    },
)
Owner = Annotated[UUID, Depends(get_current_user)]


def meetings(request: Request) -> MeetingService:
    return cast(MeetingService, request.app.state.meetings)


def emails(request: Request) -> EmailService:
    return cast(EmailService, request.app.state.emails)


class RetryMeeting(BaseModel):
    language: Literal["zh", "en"] | None = None
    model_config = ConfigDict(extra="forbid")
    date: str | None = None
    timezone: str | None = None


@router.post("/meetings/upload", status_code=202, response_model=MeetingUpload)
async def upload(
    request: Request,
    owner: Owner,
    file: Annotated[UploadFile, File()],
    date: Annotated[str | None, Form()] = None,
    timezone: Annotated[str | None, Form()] = None,
    language: Annotated[Literal["zh", "en"], Form()] = "zh",
) -> MeetingUpload:
    service = meetings(request)
    try:
        content = await file.read(service.settings.meeting_max_upload_bytes + 1)
        return await run_in_threadpool(
            service.upload,
            owner,
            file.filename or "",
            file.content_type or "",
            content,
            date,
            timezone,
            language,
        )
    finally:
        await file.close()


@router.get("/meetings", response_model=list[MeetingOut])
def listing(request: Request, owner: Owner) -> list[MeetingOut]:
    return meetings(request).listing(owner)


@router.get("/meetings/{identifier}/analysis", response_model=AnalysisOut)
def analysis(identifier: UUID, request: Request, owner: Owner) -> AnalysisOut:
    return meetings(request).get(owner, identifier)


@router.get("/meetings/{identifier}/transcript", response_model=list[TranscriptLine])
def transcript(
    identifier: UUID, request: Request, owner: Owner
) -> list[TranscriptLine]:
    return meetings(request).transcript(owner, identifier)


@router.get("/meetings/{identifier}/audit", response_model=list[AuditOut])
def audit_events(identifier: UUID, request: Request, owner: Owner) -> list[AuditOut]:
    return meetings(request).events(owner, identifier)


@router.post(
    "/meetings/{identifier}/retry", status_code=202, response_model=MeetingUpload
)
def retry(
    identifier: UUID, body: RetryMeeting, request: Request, owner: Owner
) -> MeetingUpload:
    return meetings(request).retry(
        owner, identifier, body.date, body.timezone, body.language
    )


@router.get("/tasks", response_model=list[TaskOut])
def tasks(
    request: Request,
    owner: Owner,
    status: str | None = None,
    owner_name: str | None = None,
    meeting_id: UUID | None = None,
    due_before: datetime | None = None,
) -> list[TaskOut]:
    if due_before is not None and due_before.tzinfo is None:
        raise ChatError("UTC_OFFSET_REQUIRED", "due_before requires a UTC offset.", 422)
    return meetings(request).tasks(owner, status, owner_name, meeting_id, due_before)


@router.patch("/tasks/{identifier}", response_model=TaskOut)
def edit_task(
    identifier: UUID, body: TaskPatch, request: Request, owner: Owner
) -> TaskOut:
    return meetings(request).patch_task(owner, identifier, body)


@router.get("/emails", response_model=list[EmailOut])
def list_emails(request: Request, owner: Owner) -> list[EmailOut]:
    service = emails(request)
    with service.sessions() as db:
        identifiers = list(
            db.scalars(
                select(EmailOutbox.id)
                .where(EmailOutbox.user_id == owner)
                .order_by(EmailOutbox.created_at.desc())
            )
        )
    return [service.get(owner, identifier) for identifier in identifiers]


@router.get("/emails/{identifier}", response_model=EmailOut)
def email(identifier: UUID, request: Request, owner: Owner) -> EmailOut:
    return emails(request).get(owner, identifier)


@router.patch("/emails/{identifier}", response_model=EmailOut)
def edit_email(
    identifier: UUID, body: EmailPatch, request: Request, owner: Owner
) -> EmailOut:
    return emails(request).edit(owner, identifier, body)


@router.post(
    "/emails/{identifier}/approve-send", status_code=202, response_model=EmailOut
)
def approve(
    identifier: UUID, body: Approval, request: Request, owner: Owner
) -> EmailOut:
    return emails(request).approve(owner, identifier, body)
