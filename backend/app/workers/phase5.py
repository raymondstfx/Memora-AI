from uuid import UUID

from app.core.config import get_settings
from app.db.session import build_engine
from app.services.presentations import PresentationService


def generate_presentation(identifier: str) -> None:
    settings = get_settings()
    engine = build_engine(settings)
    service = PresentationService(engine, settings)
    try:
        service.generate(UUID(identifier))
    finally:
        service.redis.close()
        engine.dispose()


def failed_presentation(job, connection, exception_type, value, traceback):  # type: ignore[no-untyped-def]
    settings = get_settings()
    engine = build_engine(settings)
    service = PresentationService(engine, settings)
    try:
        service.fail(UUID(job.args[0]), "PRESENTATION_JOB_INTERRUPTED")
    finally:
        service.redis.close()
        engine.dispose()
