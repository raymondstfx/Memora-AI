import os

from redis import Redis
from rq import Queue, SimpleWorker, Worker
from rq.serializers import JSONSerializer

from app.core.config import get_settings


def main() -> None:
    config = get_settings()
    connection = Redis.from_url(config.redis_url.get_secret_value())
    worker_class = SimpleWorker if os.name == "nt" else Worker
    worker = worker_class(
        [Queue("documents", connection=connection, serializer=JSONSerializer)],
        connection=connection,
        serializer=JSONSerializer,
    )
    worker.work(logging_level="WARNING")


if __name__ == "__main__":
    main()
