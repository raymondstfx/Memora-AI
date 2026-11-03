import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, Field, ValidationError
from redis import Redis

from app.core.config import Settings
from app.schemas.chat import ChatConfiguration
from app.services.provider_limits import rate_limit, retry_delay


class ChatError(Exception):
    def __init__(self, code: str, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class Provider(Protocol):
    def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...


def configuration(settings: Settings) -> ChatConfiguration:
    missing = []
    if settings.llm_provider != "openai_compatible":
        missing.append("LLM_PROVIDER (must be openai_compatible)")
    key = settings.llm_api_key.get_secret_value().strip()
    if not key or key.lower().startswith(("your-", "your_", "replace-", "<")):
        missing.append("LLM_API_KEY")
    if not settings.llm_model.strip() or settings.llm_model.startswith("your-"):
        missing.append("LLM_MODEL")
    try:
        url = urlsplit(settings.llm_base_url)
        httpx.URL(settings.llm_base_url)
    except (ValueError, httpx.InvalidURL):
        url = urlsplit("")
    local = url.hostname in ("localhost", "127.0.0.1", "::1", "host.docker.internal")
    if (
        not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or not (url.scheme == "https" or (url.scheme == "http" and local))
    ):
        missing.append("LLM_BASE_URL (HTTPS, or HTTP loopback for local development)")
    return ChatConfiguration(
        configured=not missing,
        missing=missing,
        provider=settings.llm_provider,
        model=settings.llm_model,
        message=(
            "Ready. Messages are sent to the configured external model."
            if not missing
            else "Configure backend .env: " + ", ".join(missing)
        ),
    )


class Delta(BaseModel):
    content: str | None = None
    refusal: str | None = None
    tool_calls: list[dict[str, object]] | None = None


class Choice(BaseModel):
    delta: Delta
    finish_reason: str | None = None


class Chunk(BaseModel):
    choices: list[Choice] = Field(default_factory=list)
    error: dict[str, object] | None = None


class OpenAICompatibleProvider:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        admission: Redis | None = None,
    ) -> None:
        self.settings, self.client = settings, client
        self.slots = asyncio.Semaphore(settings.llm_max_concurrent_requests)
        self.admission = admission

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        async with self.slots:
            lock = None
            if self.admission is not None:
                key = hashlib.sha256(
                    (self.settings.llm_base_url + self.settings.llm_model).encode()
                ).hexdigest()
                try:
                    for slot in range(self.settings.llm_max_concurrent_requests):
                        candidate = self.admission.lock(
                            f"memora:llm:slot:{key}:{slot}",
                            timeout=self.settings.llm_total_timeout_seconds + 30,
                            blocking=False,
                            thread_local=False,
                        )
                        if await asyncio.to_thread(candidate.acquire):
                            lock = candidate
                            break
                except Exception as exc:
                    raise ChatError(
                        "LLM_ADMISSION_UNAVAILABLE",
                        "Check Redis before retrying model access.",
                        503,
                    ) from exc
                if lock is None:
                    raise ChatError(
                        "LLM_BUSY",
                        "Model concurrency limit reached. Retry explicitly.",
                        429,
                    )
            try:
                async for token in self._stream(messages):
                    yield token
            finally:
                if lock:
                    await asyncio.to_thread(lock.release)

    async def _stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        config = configuration(self.settings)
        if not config.configured:
            raise ChatError("LLM_NOT_CONFIGURED", config.message, 503)
        emitted = False
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                async with self.client.stream(
                    "POST",
                    self.settings.llm_base_url.rstrip("/") + "/chat/completions",
                    headers={
                        "Authorization": "Bearer "
                        + self.settings.llm_api_key.get_secret_value().strip()
                    },
                    json={
                        "model": self.settings.llm_model,
                        "messages": messages,
                        "stream": True,
                        self.settings.llm_token_parameter: (
                            self.settings.llm_max_output_tokens
                        ),
                        **(
                            {"reasoning_effort": self.settings.llm_reasoning_effort}
                            if self.settings.llm_reasoning_effort
                            else {}
                        ),
                    },
                ) as response:
                    if response.status_code >= 400:
                        await response.aread()
                    delay = retry_delay(
                        response, attempt, self.settings.provider_retry_max_wait_seconds
                    )
                    if (
                        delay is not None
                        and not emitted
                        and attempt < self.settings.llm_max_retries
                    ):
                        await asyncio.sleep(delay)
                        continue
                    if response.status_code == 429:
                        limit = rate_limit(response)
                        raise ChatError("PROVIDER_" + limit.reason, limit.message, 429)
                    if response.status_code in (401, 403):
                        raise ChatError(
                            "PROVIDER_AUTH_ERROR",
                            "Provider rejected credentials. Check LLM_API_KEY "
                            "and model permissions.",
                        )
                    if response.status_code == 404:
                        raise ChatError(
                            "PROVIDER_MODEL_UNAVAILABLE",
                            "Model/endpoint unavailable (HTTP 404). Check LLM_MODEL, "
                            "Base URL and project model access. Configure an "
                            "accessible model explicitly; no fallback was called.",
                        )
                    if response.status_code >= 400:
                        raise ChatError(
                            "PROVIDER_HTTP_ERROR",
                            f"Provider returned HTTP {response.status_code}. "
                            "Check model, Base URL, quota and request compatibility.",
                        )
                    finish = None
                    done = False
                    size = 0
                    async for line in response.aiter_lines():
                        if len(line) > 65536:
                            raise ChatError(
                                "PROVIDER_INVALID_RESPONSE",
                                "Provider stream frame exceeded the limit.",
                            )
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            done = True
                            break
                        try:
                            chunk = Chunk.model_validate(json.loads(data))
                        except (ValueError, ValidationError) as exc:
                            raise ChatError(
                                "PROVIDER_INVALID_RESPONSE",
                                "Provider returned an invalid streaming response.",
                            ) from exc
                        if chunk.error:
                            raise ChatError(
                                "PROVIDER_STREAM_ERROR",
                                "Provider reported a stream error. "
                                "Check provider availability and quota.",
                            )
                        if not chunk.choices:
                            continue
                        choice = chunk.choices[0]
                        if choice.delta.tool_calls:
                            raise ChatError(
                                "TOOLS_UNAVAILABLE",
                                "Provider requested a tool unavailable in Phase 1.",
                            )
                        if choice.delta.refusal:
                            raise ChatError(
                                "PROVIDER_REFUSAL", "Provider declined this request."
                            )
                        if choice.delta.content:
                            size += len(choice.delta.content.encode("utf-8"))
                            if size > 131072:
                                raise ChatError(
                                    "OUTPUT_LIMIT",
                                    "Response exceeded the application output limit.",
                                )
                            emitted = True
                            yield choice.delta.content
                        if choice.finish_reason:
                            finish = choice.finish_reason
                    if finish == "length":
                        raise ChatError(
                            "OUTPUT_LIMIT",
                            "Model output limit reached; response is incomplete.",
                        )
                    if finish != "stop" or not done or not emitted:
                        raise ChatError(
                            "PROVIDER_INCOMPLETE",
                            "Provider stream ended without a complete response.",
                        )
                    return
            except httpx.TimeoutException as exc:
                raise ChatError(
                    "PROVIDER_TIMEOUT",
                    "Provider timed out. Check connectivity or retry explicitly.",
                ) from exc
            except httpx.HTTPError as exc:
                raise ChatError(
                    "PROVIDER_CONNECTION_ERROR",
                    "Cannot connect to provider. "
                    "Check LLM_BASE_URL and network settings.",
                ) from exc
