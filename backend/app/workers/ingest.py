from uuid import UUID

from app.core.config import get_settings
from app.db.session import build_engine
from app.services.documents import DocumentService


def ingest_document(identifier: str) -> None:
    settings = get_settings()
    engine = build_engine(settings)
    service = DocumentService(engine, settings)
    try:
        service.ingest(UUID(identifier))
    finally:
        service.redis.close()
        engine.dispose()


def failed_job(job, connection, exception_type, value, traceback):  # type: ignore[no-untyped-def]
    settings = get_settings()
    engine = build_engine(settings)
    service = DocumentService(engine, settings)
    try:
        service.fail(
            UUID(job.id),
            "WORKER_FAILED",
            "RQ worker stopped or timed out. Retry explicitly.",
        )
    finally:
        service.redis.close()
        engine.dispose()
