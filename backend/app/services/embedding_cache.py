"""Private, profile-scoped vector cache and cross-process request admission."""

import hashlib
import json
import math
import time

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.services.embedding import EmbeddingProvider, embedding_configuration, profile
from app.services.llm.provider import ChatError


class EmbeddingCache:
    def __init__(self, settings: Settings, redis: Redis, provider: EmbeddingProvider):
        self.settings, self.redis, self.provider = settings, redis, provider

    def key(self, scope: str, text: str) -> str:
        digest = hashlib.sha256(text.encode()).hexdigest()
        return f"memora:embedding:cache:{scope}:{profile(self.settings)}:{digest}"

    def valid(self, vector: object) -> bool:
        return (
            isinstance(vector, list)
            and len(vector) == self.settings.embedding_dimensions
            and all(isinstance(x, (int, float)) and math.isfinite(x) for x in vector)
            and sum(x * x for x in vector) > 1e-12
        )

    def read(self, key: str) -> list[float] | None:
        value = self.redis.get(key)
        if isinstance(value, (str, bytes, bytearray)):
            try:
                vector = json.loads(value)
                if self.valid(vector):
                    return list(vector)
            except (ValueError, TypeError):
                pass
            self.redis.delete(key)
        return None

    def embed(self, scope: str, texts: list[str]) -> list[list[float]]:
        config = embedding_configuration(self.settings)
        if not config.configured:
            raise ChatError("EMBEDDING_NOT_CONFIGURED", config.message, 503)
        if not texts or any(not t.strip() for t in texts):
            raise ChatError("EMBEDDING_EMPTY_INPUT", "Cannot embed empty text.", 422)
        keys = [self.key(scope, text) for text in texts]
        try:
            found = {key: self.read(key) for key in set(keys)}
            if all(found.values()):
                return [list(found[key] or []) for key in keys]
            # Slots are shared by API and workers. Fail fast; no unbounded queue.
            lease = (
                self.settings.embedding_timeout_seconds
                + self.settings.provider_retry_max_wait_seconds
                + self.settings.embedding_min_interval_seconds
                + 10
            ) * (self.settings.embedding_max_retries + 1)
            lock = None
            for slot in range(self.settings.embedding_max_concurrent_requests):
                candidate = self.redis.lock(
                    f"memora:embedding:slot:{profile(self.settings)}:{slot}",
                    timeout=lease,
                    blocking=False,
                )
                if candidate.acquire():
                    lock = candidate
                    break
            if lock is None:
                raise ChatError(
                    "EMBEDDING_BUSY",
                    "Embedding concurrency limit reached. Retry explicitly.",
                    429,
                )
            try:
                # Recheck after admission; deduplicate identical chunks in this batch.
                found = {key: self.read(key) for key in set(keys)}
                missing = dict(
                    (key, text)
                    for key, text in zip(keys, texts, strict=True)
                    if found[key] is None
                )
                if missing:
                    interval = self.settings.embedding_min_interval_seconds
                    pacing = f"memora:embedding:pacing:{profile(self.settings)}"
                    deadline = time.monotonic() + interval + 2
                    while interval and not self.redis.set(
                        pacing, "1", nx=True, px=max(1, int(interval * 1000))
                    ):
                        if time.monotonic() > deadline:
                            raise ChatError(
                                "EMBEDDING_BUSY",
                                "Embedding pacing limit reached. Retry explicitly.",
                                429,
                            )
                        time.sleep(0.1)
                    vectors = self.provider.embed(list(missing.values()))
                    if len(vectors) != len(missing) or not all(
                        self.valid(v) for v in vectors
                    ):
                        raise ChatError(
                            "EMBEDDING_INVALID_RESPONSE",
                            "Invalid vector count/dimensions; no cache written.",
                        )
                    for key, vector in zip(missing, vectors, strict=True):
                        self.redis.set(
                            key,
                            json.dumps(vector),
                            ex=self.settings.embedding_cache_ttl_seconds,
                        )
                        found[key] = vector
                return [list(found[key] or []) for key in keys]
            finally:
                lock.release()
        except RedisError as exc:
            # No unscheduled upstream call when admission/cache infrastructure fails.
            raise ChatError(
                "EMBEDDING_CACHE_UNAVAILABLE",
                "Embedding cache/admission unavailable. "
                "Check Redis and retry explicitly.",
                503,
            ) from exc

    def drop(self, scope: str) -> None:
        try:
            for key in self.redis.scan_iter(
                match=f"memora:embedding:cache:{scope}:*", count=100
            ):
                self.redis.unlink(key)
        except RedisError as exc:
            raise ChatError(
                "EMBEDDING_CACHE_UNAVAILABLE",
                "Cannot remove private vector cache. Check Redis.",
                503,
            ) from exc
