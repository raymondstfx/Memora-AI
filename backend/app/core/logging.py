import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "event": record.getMessage()
                if record.getMessage()
                in {
                    "http_request",
                    "chat_run_finished",
                    "presentation_stage",
                    "presentation_failed",
                }
                else "redacted_event",
                "job_id": getattr(record, "job_id", None),
                "stage": getattr(record, "stage", None),
                "attempt": getattr(record, "attempt", None),
                "request_id": getattr(record, "request_id", None),
                "status_code": getattr(record, "status_code", None),
                "duration_ms": getattr(record, "duration_ms", None),
                "conversation_id": getattr(record, "conversation_id", None),
                "message_id": getattr(record, "message_id", None),
                "message_status": getattr(record, "message_status", None),
                "error_code": getattr(record, "error_code", None),
                "output_chars": getattr(record, "output_chars", None),
            }
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("memora")
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
