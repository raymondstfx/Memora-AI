"""Sanitized quota classification; never echo upstream bodies/credentials."""

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx


@dataclass(frozen=True)
class RateLimit:
    reason: str
    delay: float | None

    @property
    def message(self) -> str:
        advice = {
            "DAILY_QUOTA": "Daily quota exhausted. Wait for reset or check quota.",
            "QUOTA_UNAVAILABLE": "Quota unavailable/billing required. Check AI Studio.",
            "TOKEN_RATE": "Input token rate exceeded. Reduce PDF batch/context size.",
            "REQUEST_RATE": "Request rate exceeded. Reduce concurrency/frequency.",
            "UNKNOWN": "Rate limit reason unavailable. Check AI Studio project limits.",
        }[self.reason]
        wait = (
            f" Server retry delay: {self.delay:g}s." if self.delay is not None else ""
        )
        return advice + wait + " Retry explicitly if automatic retry was not possible."


def rate_limit(response: httpx.Response) -> RateLimit:
    # Inspect a bounded error payload, use only classifications and numeric hints.
    raw = response.content[:65536].decode("utf-8", errors="replace")
    lower = raw.lower()
    compact = re.sub(r"[^a-z0-9]", "", lower)
    if any(term in compact for term in ("perday", "daily", "requestsperday")):
        reason = "DAILY_QUOTA"
    elif re.search(r'(?:limit|quotavalue)"?\s*[:=]\s*"?0\b', lower) or any(
        term in compact for term in ("insufficientquota", "billing", "quotalimit0")
    ):
        reason = "QUOTA_UNAVAILABLE"
    elif "token" in compact and any(t in compact for t in ("perminute", "ratelimit")):
        reason = "TOKEN_RATE"
    elif any(t in compact for t in ("perminute", "ratelimitexceeded", "ratelimit")):
        reason = "REQUEST_RATE"
    else:
        reason = "UNKNOWN"
    delays = []
    hint = response.headers.get("retry-after", "")
    try:
        delays.append(float(hint))
    except ValueError:
        try:
            delays.append(
                (parsedate_to_datetime(hint) - datetime.now(UTC)).total_seconds()
            )
        except (ValueError, TypeError, OverflowError):
            pass
    try:
        payload = json.loads(raw)
        error = payload.get("error", payload)
        for detail in error.get("details", []):
            if str(detail.get("@type", "")).endswith("RetryInfo"):
                delay = detail.get("retryDelay", "")
                if isinstance(delay, str) and delay.endswith("s"):
                    delays.append(float(delay[:-1]))
                elif isinstance(delay, dict):
                    delays.append(
                        float(delay.get("seconds", 0))
                        + float(delay.get("nanos", 0)) / 1e9
                    )
    except (ValueError, TypeError, AttributeError):
        pass
    valid = [max(0, d) for d in delays if math.isfinite(d)]
    return RateLimit(reason, max(valid) if valid else None)


def retry_delay(response: httpx.Response, attempt: int, maximum: float) -> float | None:
    if response.status_code == 429:
        limit = rate_limit(response)
        if limit.reason in ("DAILY_QUOTA", "QUOTA_UNAVAILABLE"):
            return None
        # Unknown 429 is retried only with explicit server timing.
        if limit.reason == "UNKNOWN" and limit.delay is None:
            return None
        delay = limit.delay if limit.delay is not None else 0.5 * 2**attempt
    elif response.status_code in (502, 503, 504):
        delay = rate_limit(response).delay
        delay = delay if delay is not None else 0.5 * 2**attempt
    else:
        return None
    # Never shorten the server's requested wait and retry prematurely.
    return delay if delay <= maximum else None
