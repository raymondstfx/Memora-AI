import asyncio
from collections.abc import Awaitable
from typing import cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import Engine, text
from starlette.concurrency import run_in_threadpool

from app.core.errors import error_response
from app.schemas.health import Dependencies, ErrorResponse, HealthResponse

SCHEMA_REVISION = "0001_infrastructure"
router = APIRouter(prefix="/api", tags=["infrastructure"])


def postgres_readiness(engine: Engine) -> dict[str, str]:
    state = dict.fromkeys(("postgres", "pgvector", "schema"), "unavailable")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            state["postgres"] = "ready"
            vector = connection.scalar(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            state["pgvector"] = "ready" if vector else "unavailable"
            revision = connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            state["schema"] = "ready" if revision == SCHEMA_REVISION else "unavailable"
    except Exception:
        # Never return raw driver exceptions: connection strings can contain secrets.
        pass
    return state


async def redis_readiness(client: Redis) -> str:
    try:
        return "ready" if await cast(Awaitable[bool], client.ping()) else "unavailable"
    except Exception:
        return "unavailable"


@router.get(
    "/health", response_model=HealthResponse, responses={503: {"model": ErrorResponse}}
)
async def health(request: Request) -> HealthResponse | JSONResponse:
    postgres, redis = await asyncio.gather(
        run_in_threadpool(postgres_readiness, request.app.state.engine),
        redis_readiness(request.app.state.redis),
    )
    dependencies = Dependencies.model_validate({**postgres, "redis": redis})
    if "unavailable" in dependencies.model_dump(by_alias=True).values():
        return error_response(
            request,
            503,
            "DEPENDENCIES_UNAVAILABLE",
            "One or more dependencies are not ready.",
            {"dependencies": dependencies.model_dump(by_alias=True)},
        )
    return HealthResponse(dependencies=dependencies)
