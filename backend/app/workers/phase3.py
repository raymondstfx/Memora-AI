from uuid import UUID

from app.core.config import get_settings
from app.db.session import build_engine
from app.services.emails import EmailService
from app.services.meetings import MeetingService


def analyze_meeting(identifier: str) -> None:
    settings = get_settings()
    engine = build_engine(settings)
    service = MeetingService(engine, settings)
    try:
        service.analyze(UUID(identifier))
    finally:
        service.redis.close()
        engine.dispose()


def send_email(identifier: str) -> None:
    settings = get_settings()
    engine = build_engine(settings)
    service = EmailService(engine, settings)
    try:
        service.send(UUID(identifier))
    finally:
        service.redis.close()
        engine.dispose()


def failed_meeting(job, connection, exception_type, value, traceback):  # type: ignore[no-untyped-def]
    settings = get_settings()
    engine = build_engine(settings)
    service = MeetingService(engine, settings)
    try:
        service.fail(
            UUID(job.id),
            "MEETING_JOB_INTERRUPTED",
            "Meeting worker interrupted. Retry explicitly; no automatic replay.",
        )
    finally:
        service.redis.close()
        engine.dispose()
