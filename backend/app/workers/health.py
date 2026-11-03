from datetime import UTC, datetime

from redis import Redis
from rq import Worker

from app.core.config import get_settings


def main() -> None:
    config = get_settings()
    connection = Redis.from_url(config.redis_url.get_secret_value(), socket_timeout=3)
    try:
        workers = Worker.all(connection=connection)
        healthy = any(
            worker.last_heartbeat
            and (datetime.now(UTC) - worker.last_heartbeat).total_seconds() < 500
            for worker in workers
            if "documents" in worker.queue_names()
        )
        raise SystemExit(0 if healthy else 1)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
