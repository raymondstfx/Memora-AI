import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
                "request_id": getattr(record, "request_id", None),
                "status_code": getattr(record, "status_code", None),
                "duration_ms": getattr(record, "duration_ms", None),
            }
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("memora")
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
