import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.api.health import router
from app.core.config import Settings, get_settings
from app.core.errors import error_response, install_error_handlers
from app.core.logging import configure_logging
from app.db.session import build_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = build_engine(config)
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
            await app.state.redis.aclose()
            app.state.engine.dispose()

    app = FastAPI(title="Memora AI API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET"],
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
    return app


app = create_app()
