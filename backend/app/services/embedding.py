import hashlib
import json
import math
import time
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.schemas.documents import DocumentConfiguration
from app.services.llm.provider import ChatError
from app.services.provider_limits import rate_limit, retry_delay


def profile(settings: Settings) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                settings.embedding_provider,
                settings.embedding_base_url.rstrip("/"),
                settings.embedding_model,
                settings.embedding_dimensions,
                *(["l2-normalized-v1"] if settings.embedding_normalize else []),
            ]
        ).encode()
    ).hexdigest()


def embedding_configuration(settings: Settings) -> DocumentConfiguration:
    missing = []
    if settings.embedding_provider != "openai_compatible":
        missing.append("EMBEDDING_PROVIDER (openai_compatible)")
    key = settings.embedding_api_key.get_secret_value().strip()
    if not key or key.lower().startswith(("your-", "replace-", "<")):
        missing.append("EMBEDDING_API_KEY")
    if not settings.embedding_model or settings.embedding_model.startswith("your-"):
        missing.append("EMBEDDING_MODEL")
    if not settings.embedding_dimensions:
        missing.append("EMBEDDING_DIMENSIONS")
    try:
        url = urlsplit(settings.embedding_base_url)
        httpx.URL(settings.embedding_base_url)
        local = url.hostname in (
            "127.0.0.1",
            "localhost",
            "::1",
            "host.docker.internal",
        )
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not (url.scheme == "https" or (local and url.scheme == "http"))
        ):
            missing.append("EMBEDDING_BASE_URL")
    except (ValueError, httpx.InvalidURL):
        missing.append("EMBEDDING_BASE_URL")
    return DocumentConfiguration(
        configured=not missing,
        missing=missing,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        profile=profile(settings),
        max_upload_bytes=settings.pdf_max_upload_bytes,
        message=(
            "Embedding configured. PDF text is sent to this provider during indexing."
            if not missing
            else "Configure backend .env: " + ", ".join(missing)
        ),
    )


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class EmbeddingItem(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    index: int | None = Field(default=None, ge=0)
    embedding: list[float]


class EmbeddingResponse(BaseModel):
    data: list[EmbeddingItem]


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings, self.client = settings, client

    def embed(self, texts: list[str]) -> list[list[float]]:
        config = embedding_configuration(self.settings)
        if not config.configured:
            raise ChatError("EMBEDDING_NOT_CONFIGURED", config.message, 503)
        if not texts or any(not value.strip() for value in texts):
            raise ChatError("EMBEDDING_EMPTY_INPUT", "Cannot embed empty text.", 422)
        if self.settings.embedding_max_input_bytes and any(
            len(value.encode()) > self.settings.embedding_max_input_bytes
            for value in texts
        ):
            raise ChatError(
                "EMBEDDING_INPUT_LIMIT",
                "Embedding input exceeds the conservative byte budget. "
                "Shorten the query or explicitly reparse/reindex this PDF.",
                422,
            )
        owned = self.client is None
        client = self.client or httpx.Client(
            timeout=httpx.Timeout(self.settings.embedding_timeout_seconds, connect=5),
            follow_redirects=False,
        )
        try:
            body: dict[str, object] = {
                "input": texts,
                "model": self.settings.embedding_model,
                "encoding_format": "float",
            }
            if self.settings.embedding_send_dimensions:
                body["dimensions"] = self.settings.embedding_dimensions
            for attempt in range(self.settings.embedding_max_retries + 1):
                response = client.post(
                    self.settings.embedding_base_url.rstrip("/") + "/embeddings",
                    headers={
                        "Authorization": "Bearer "
                        + self.settings.embedding_api_key.get_secret_value().strip()
                    },
                    json=body,
                )
                delay = retry_delay(
                    response, attempt, self.settings.provider_retry_max_wait_seconds
                )
                if delay is not None and attempt < self.settings.embedding_max_retries:
                    time.sleep(delay)
                    continue
                if response.status_code == 429:
                    limit = rate_limit(response)
                    raise ChatError("EMBEDDING_" + limit.reason, limit.message, 429)
                if response.status_code in (401, 403):
                    raise ChatError(
                        "EMBEDDING_AUTH_ERROR",
                        "Embedding provider rejected credentials or model access.",
                    )
                if response.status_code >= 400:
                    raise ChatError(
                        "EMBEDDING_HTTP_ERROR",
                        f"Embedding HTTP {response.status_code}. "
                        "Check model, dimensions and Base URL.",
                    )
                try:
                    data = EmbeddingResponse.model_validate(response.json()).data
                    # Gemini compatibility may omit/null every index. Only this
                    # known endpoint may use the returned input-order array.
                    gemini = (
                        urlsplit(self.settings.embedding_base_url).hostname
                        == "generativelanguage.googleapis.com"
                    )
                    if (
                        gemini
                        and len(data) == len(texts)
                        and all(item.index is None for item in data)
                    ):
                        for index, item in enumerate(data):
                            item.index = index
                    if any(item.index is None for item in data):
                        raise ValueError("Response omitted input indices")
                    data.sort(
                        key=lambda item: item.index if item.index is not None else -1
                    )
                    if [item.index for item in data] != list(range(len(texts))):
                        raise ValueError("Response indices do not match input")
                    vectors = [item.embedding for item in data]
                    if any(
                        len(v) != self.settings.embedding_dimensions
                        or not all(math.isfinite(x) for x in v)
                        or sum(x * x for x in v) <= 1e-12
                        for v in vectors
                    ):
                        raise ValueError("Invalid vector dimension or norm")
                except (ValueError, TypeError) as exc:
                    raise ChatError(
                        "EMBEDDING_INVALID_RESPONSE",
                        "Invalid embedding shape/dimensions. No vectors committed.",
                    ) from exc
                if self.settings.embedding_normalize:
                    vectors = [normalize(v) for v in vectors]
                return vectors
            raise ChatError("EMBEDDING_HTTP_ERROR", "Embedding retries exhausted.")
        except httpx.TimeoutException as exc:
            raise ChatError(
                "EMBEDDING_TIMEOUT", "Embedding provider timed out. Retry explicitly."
            ) from exc
        except httpx.HTTPError as exc:
            raise ChatError(
                "EMBEDDING_CONNECTION_ERROR",
                "Cannot reach embedding provider. Check Base URL and network.",
            ) from exc
        finally:
            if owned:
                client.close()


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector]
