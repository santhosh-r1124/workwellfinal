"""Retry and pacing around a model provider.

Written for a free API tier, where the binding constraint is requests per
minute rather than money. Without this, the daily sweep hands every
employee to a worker pool at once, the provider answers 429, and
`safe_generate` does exactly what it is designed to do - shows the
deterministic fallback - so the product degrades to canned sentences
while looking healthy. The numbers stay correct; the prose quietly stops
being written.

Two mechanisms, both deliberately simple:

* A shared budget in Redis, so the API process and the worker draw from
  one allowance instead of each assuming it owns the whole quota. Falls
  back to a per-process limiter when Redis is unreachable, because
  degrading to "slightly too many requests" beats refusing to work.
* Bounded retry with exponential backoff and jitter, honouring
  `Retry-After` when the provider sends one. Jitter matters here: a sweep
  that retries in lockstep just rebuilds the burst it was throttled for.

Anything still failing after that is a real failure and is allowed to
propagate to `safe_generate`.
"""

from __future__ import annotations

import logging
import random
import re
import time

from agents.providers.base import AIProvider
from apps.backend.core.observability import REGISTRY

logger = logging.getLogger("workwell.provider")

# Substrings that mean "ask again shortly", not "this request was wrong".
TRANSIENT_MARKERS = (
    "429",
    "rate limit",
    "ratelimit",
    "quota",
    "resource_exhausted",
    "resource exhausted",
    "500",
    "502",
    "503",
    "504",
    "unavailable",
    "deadline",
    "timeout",
    "timed out",
    "overloaded",
    "connection reset",
)

RETRY_AFTER_RE = re.compile(r"retry[- ]after[\"':\s]+(\d+(?:\.\d+)?)", re.I)


def status_code_of(exc: Exception) -> int | None:
    for attribute in ("status_code", "code", "http_status"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def is_transient(exc: Exception) -> bool:
    """Deliberately generous with the message text rather than tied to one
    SDK's exception classes: the cost of retrying a permanent error a few
    times is small, and the cost of not retrying a throttle is every
    explanation in the product turning into canned text."""
    code = status_code_of(exc)
    if code is not None:
        return code == 429 or 500 <= code < 600

    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in TRANSIENT_MARKERS)


def retry_after_seconds(exc: Exception) -> float | None:
    """The provider's own instruction, when it gives one, beats our guess."""
    for attribute in ("retry_after", "retry_delay"):
        value = getattr(exc, attribute, None)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)

    match = RETRY_AFTER_RE.search(str(exc))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


class RateLimiter:
    """Fixed one-minute window, shared through Redis when it is available.

    A fixed window can let through up to 2x the limit across a boundary.
    That is acceptable against a quota expressed per minute with its own
    slack, and it costs one INCR rather than a sorted set per call.
    """

    def __init__(self, requests_per_minute: int, max_wait_seconds: float) -> None:
        self._limit = max(1, requests_per_minute)
        self._max_wait = max_wait_seconds
        self._local: list[float] = []

    def _redis(self):
        try:
            from apps.backend.core.redis_client import get_redis

            return get_redis()
        except Exception:
            return None

    def _try_local(self, now: float) -> bool:
        self._local = [t for t in self._local if now - t < 60]
        if len(self._local) >= self._limit:
            return False
        self._local.append(now)
        return True

    def _try_shared(self, client, now: float) -> bool:
        key = f"workwell:llm:rpm:{int(now // 60)}"
        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 120)
            count, _ = pipe.execute()
            return int(count) <= self._limit
        except Exception:
            return self._try_local(now)

    def acquire(self) -> bool:
        """Blocks until a slot is free. False means the wait budget ran out,
        and the caller should proceed anyway rather than lose the work -
        being throttled is a better outcome than silently skipping."""
        client = self._redis()
        deadline = time.monotonic() + self._max_wait

        while True:
            now = time.time()
            allowed = self._try_shared(client, now) if client else self._try_local(now)
            if allowed:
                return True

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning("rate limit wait budget exhausted; sending anyway")
                return False

            # Sleep to the start of the next window, plus jitter so several
            # workers do not all wake into the same instant.
            wait = min(remaining, 60 - (now % 60) + random.uniform(0.05, 0.75))
            REGISTRY.increment("workwell_llm_throttled_total")
            time.sleep(max(0.05, wait))


class ResilientProvider:
    def __init__(
        self,
        inner: AIProvider,
        name: str,
        requests_per_minute: int,
        max_retries: int,
        base_backoff_seconds: float,
        max_wait_seconds: float,
    ) -> None:
        self._inner = inner
        self._name = name
        self._retries = max(0, max_retries)
        self._base = base_backoff_seconds
        self._limiter = RateLimiter(requests_per_minute, max_wait_seconds)

    def _call(self, fn, *args, **kwargs):
        last: Exception | None = None

        for attempt in range(self._retries + 1):
            self._limiter.acquire()
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last = exc
                if attempt == self._retries or not is_transient(exc):
                    raise

                delay = retry_after_seconds(exc)
                if delay is None:
                    # Exponential, with full jitter: retrying in lockstep
                    # just rebuilds the burst that caused the throttle.
                    delay = self._base * (2**attempt)
                    delay = random.uniform(delay / 2, delay)

                REGISTRY.increment("workwell_llm_retries_total", {"provider": self._name})
                logger.warning(
                    "provider call failed (%s), retrying in %.1fs [%s/%s]",
                    type(exc).__name__,
                    delay,
                    attempt + 1,
                    self._retries,
                )
                time.sleep(delay)

        raise last  # unreachable; the loop either returns or raises

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._call(self._inner.generate, prompt, system=system)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._call(self._inner.embed, texts)
