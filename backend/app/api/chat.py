from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core.auth import get_current_user
from app.schemas.chat import (
    ChatConfiguration,
    ChatRequest,
    ConversationOut,
    MessageOut,
    RetryRequest,
)
from app.schemas.health import ErrorResponse
from app.services.chat import ChatService, Turn
from app.services.llm.provider import configuration

router = APIRouter(
    prefix="/api",
    tags=["chat"],
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
Owner = Annotated[UUID, Depends(get_current_user)]


def service(request: Request) -> ChatService:
    return cast(ChatService, request.app.state.chat)


@router.get("/chat/config", response_model=ChatConfiguration)
def chat_config(request: Request) -> ChatConfiguration:
    return configuration(service(request).settings)


@router.get("/conversations", response_model=list[ConversationOut])
def conversations(request: Request, owner: Owner) -> list[ConversationOut]:
    return service(request).conversations(owner)


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageOut]
)
def history(conversation_id: UUID, request: Request, owner: Owner) -> list[MessageOut]:
    return service(request).history(owner, conversation_id)


def response(request: Request, turn: Turn) -> StreamingResponse:
    return StreamingResponse(
        service(request).events(turn, request.state.request_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "SSE with JSON StreamEvent frames. No automatic replay.",
        },
    },
)
async def chat(body: ChatRequest, request: Request, owner: Owner) -> StreamingResponse:
    turn = await run_in_threadpool(
        service(request).prepare, owner, body, body.request_id
    )
    return response(request, turn)


@router.post("/messages/{message_id}/retry", response_class=StreamingResponse)
async def retry(
    message_id: UUID, body: RetryRequest, request: Request, owner: Owner
) -> StreamingResponse:
    turn = await run_in_threadpool(
        service(request).prepare, owner, None, body.request_id, message_id
    )
    return response(request, turn)


@router.post("/messages/{message_id}/cancel", response_model=MessageOut)
async def cancel(message_id: UUID, request: Request, owner: Owner) -> MessageOut:
    chat = service(request)
    result = await run_in_threadpool(chat.cancel, owner, message_id)
    if task := chat.tasks.get(message_id):
        task.cancel()
    return result
