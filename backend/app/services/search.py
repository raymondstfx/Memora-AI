import hashlib
import json
from datetime import UTC, datetime
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.schemas.presentations import WebSearchResult, WebSource
from app.services.llm.provider import ChatError


class SearchService:
    def __init__(
        self, settings: Settings, redis: Redis, client: httpx.Client | None = None
    ) -> None:
        self.settings, self.redis, self.client = settings, redis, client

    def search(self, owner: UUID, query: str) -> WebSearchResult:
        if not 2 <= len(query.strip()) <= 500:
            raise ChatError(
                "SEARCH_QUERY_INVALID", "Search query must be 2-500 characters.", 422
            )
        try:
            return self._search(owner, query.strip())
        except RedisError as exc:
            raise ChatError(
                "SEARCH_CACHE_UNAVAILABLE",
                "Redis unavailable; search stopped before further requests.",
                503,
            ) from exc

    def _search(self, owner: UUID, query: str) -> WebSearchResult:
        s = self.settings
        if not s.search_api_key.get_secret_value().strip():
            raise ChatError(
                "SEARCH_NOT_CONFIGURED",
                "Set SEARCH_API_KEY in backend root .env (Tavily).",
                503,
            )
        try:
            endpoint = urlsplit(s.search_base_url)
            local = endpoint.hostname in (
                "127.0.0.1",
                "localhost",
                "::1",
                "host.docker.internal",
            )
            if (
                not endpoint.hostname
                or endpoint.username is not None
                or endpoint.password is not None
                or endpoint.query
                or endpoint.fragment
                or not (
                    endpoint.scheme == "https" or (local and endpoint.scheme == "http")
                )
            ):
                raise ValueError("Invalid endpoint")
        except ValueError as exc:
            raise ChatError(
                "SEARCH_BASE_URL_INVALID",
                "Set a trusted HTTPS SEARCH_BASE_URL at .env line 110.",
                503,
            ) from exc
        digest = hashlib.sha256(
            (
                str(owner) + s.search_base_url + query + str(s.search_max_results)
            ).encode()
        ).hexdigest()
        key = "search:v1:" + digest
        cached = self.redis.get(key)
        if cached:
            return WebSearchResult.model_validate_json(
                str(cached) if isinstance(cached, str) else cast(bytes, cached)
            ).model_copy(update={"cached": True})
        # Shared finite admission: no retries or unbounded queueing on search.
        lock = self.redis.lock(
            "search:admission", timeout=s.search_timeout_seconds + 5, blocking_timeout=0
        )
        if not lock.acquire(blocking=False):
            raise ChatError(
                "SEARCH_BUSY", "Search is busy. Try again explicitly later.", 429
            )
        try:

            def request(client: httpx.Client) -> WebSearchResult:
                with client.stream(
                    "POST",
                    s.search_base_url.rstrip("/") + "/search",
                    headers={
                        "Authorization": "Bearer " + s.search_api_key.get_secret_value()
                    },
                    json={
                        "query": query,
                        "search_depth": "basic",
                        "max_results": s.search_max_results,
                        "include_raw_content": False,
                        "include_answer": False,
                        "include_images": False,
                    },
                    timeout=s.search_timeout_seconds,
                ) as response:
                    if response.status_code != 200:
                        code = (
                            "SEARCH_RATE_LIMITED"
                            if response.status_code == 429
                            else "SEARCH_PROVIDER_ERROR"
                        )
                        raise ChatError(
                            code,
                            "Search rejected. Check key/quota; retry explicitly later.",
                            503,
                        )
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > 100000:
                            raise ChatError(
                                "SEARCH_RESPONSE_TOO_LARGE",
                                "Search response exceeded the limit.",
                                502,
                            )
                payload = json.loads(content)
                if (
                    not isinstance(payload, dict)
                    or not isinstance(payload.get("results"), list)
                    or any(not isinstance(r, dict) for r in payload["results"])
                ):
                    raise ChatError(
                        "SEARCH_INVALID_RESPONSE",
                        "Search returned an invalid result structure.",
                        502,
                    )
                now = datetime.now(UTC)
                sources = []
                for row in payload.get("results", [])[: s.search_max_results]:
                    url = str(row.get("url", ""))
                    parsed = urlsplit(url)
                    if (
                        parsed.scheme not in ("https", "http")
                        or not parsed.hostname
                        or parsed.username is not None
                        or parsed.password is not None
                        or any(ord(c) < 32 for c in url)
                        or len(url) > 2000
                    ):
                        continue
                    sources.append(
                        WebSource(
                            title=str(row.get("title", ""))[:300],
                            url=url,
                            snippet=str(row.get("content", ""))[:1500],
                            published_at=str(row["published_date"])[:80]
                            if row.get("published_date")
                            else None,
                            retrieved_at=now,
                        )
                    )
                return WebSearchResult(sources=sources)

            if self.client:
                result = request(self.client)
            else:
                with httpx.Client(follow_redirects=False) as client:
                    result = request(client)
            if s.search_cache_ttl_seconds:
                self.redis.setex(
                    key, s.search_cache_ttl_seconds, result.model_dump_json()
                )
            return result
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ChatError(
                "SEARCH_UNAVAILABLE",
                "Search failed or returned invalid data. No results were invented.",
                503,
            ) from exc
        finally:
            if lock.owned():
                lock.release()
