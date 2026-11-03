import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.agents.checkpoints import ThreadedPostgresSaver
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.health import router
from app.api.meetings import router as meetings_router
from app.api.memories import router as memories_router
from app.api.presentations import router as presentations_router
from app.core.config import Settings, get_settings
from app.core.errors import error_response, install_error_handlers
from app.core.logging import configure_logging
from app.core.upload_limit import UploadLimit
from app.db.session import build_engine
from app.schemas.chat import StreamEvent
from app.services.chat import ChatService
from app.services.documents import DocumentService
from app.services.emails import EmailService
from app.services.llm.provider import OpenAICompatibleProvider
from app.services.meetings import MeetingService
from app.services.memories import MemoryService
from app.services.presentations import PresentationService


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = build_engine(config)
        app.state.http = httpx.AsyncClient(
            timeout=httpx.Timeout(
                config.llm_read_timeout_seconds,
                connect=config.llm_connect_timeout_seconds,
            ),
            follow_redirects=False,
        )
        from sqlalchemy.engine import make_url

        conninfo = (
            make_url(config.database_url.get_secret_value())
            .set(drivername="postgresql")
            .render_as_string(hide_password=False)
        )
        app.state.checkpoint_pool = ConnectionPool(
            conninfo,
            min_size=0,
            max_size=2,
            timeout=config.dependency_timeout_seconds,
            kwargs={
                "autocommit": True,
                "row_factory": dict_row,
                "prepare_threshold": 0,
                "connect_timeout": config.dependency_timeout_seconds,
            },
            open=False,
        )
        app.state.checkpoint_pool.open()
        app.state.documents = DocumentService(app.state.engine, config)
        app.state.meetings = MeetingService(app.state.engine, config)
        app.state.presentations = PresentationService(app.state.engine, config)
        app.state.emails = EmailService(app.state.engine, config)
        app.state.memories = MemoryService(app.state.engine, config)
        app.state.chat = ChatService(
            app.state.engine,
            config,
            OpenAICompatibleProvider(config, app.state.http, app.state.documents.redis),
            ThreadedPostgresSaver(app.state.checkpoint_pool),
        )
        app.state.chat.documents = app.state.documents
        app.state.chat.memories = app.state.memories
        app.state.redis = Redis.from_url(
            config.redis_url.get_secret_value(),
            socket_connect_timeout=config.dependency_timeout_seconds,
            socket_timeout=config.dependency_timeout_seconds,
            retry_on_timeout=False,
            retry=Retry(NoBackoff(), 0),
        )
        try:
            yield
        finally:
            tasks = list(app.state.chat.tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await app.state.http.aclose()
            await asyncio.to_thread(app.state.checkpoint_pool.close)
            await app.state.redis.aclose()
            app.state.documents.redis.close()
            app.state.meetings.redis.close()
            app.state.emails.redis.close()
            app.state.presentations.redis.close()
            app.state.engine.dispose()

    app = FastAPI(title="Memora AI API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        UploadLimit,
        max_bytes=config.pdf_max_upload_bytes,
        meeting_max_bytes=config.meeting_max_upload_bytes,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            response = error_response(
                request, 500, "INTERNAL_ERROR", "An internal error occurred."
            )
        response.headers["X-Request-ID"] = request.state.request_id
        logging.getLogger("memora").info(
            "http_request",
            extra={
                "request_id": request.state.request_id,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    install_error_handlers(app)
    app.include_router(router)
    app.include_router(chat_router)
    app.include_router(documents_router)
    app.include_router(meetings_router)
    app.include_router(memories_router)
    app.include_router(presentations_router)

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = get_openapi(
                title=app.title, version=app.version, routes=app.routes
            )
            schema.setdefault("components", {}).setdefault("schemas", {})[
                "StreamEvent"
            ] = StreamEvent.model_json_schema()
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]
    return app


app = create_app()
