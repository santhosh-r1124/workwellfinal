"""Free-tier behaviour: throttles are a wait, not a failure.

Without retry, a 429 reaches `safe_generate`, which does exactly what it
is designed to do - shows the deterministic fallback - so the product
degrades to canned sentences while every health check stays green. On a
rate-limited free tier that is not an edge case, it is the normal
outcome of the daily sweep.
"""

import pytest

from agents.providers.resilient import (
    RateLimiter,
    ResilientProvider,
    is_transient,
    retry_after_seconds,
    status_code_of,
)


class Boom(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class FlakyProvider:
    """Fails `failures` times, then succeeds."""

    def __init__(self, failures: int, exc: Exception) -> None:
        self.failures = failures
        self.exc = exc
        self.calls = 0

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc
        return "written by the model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc
        return [[0.1] * 8 for _ in texts]


def wrap(inner, **kwargs) -> ResilientProvider:
    defaults = dict(
        requests_per_minute=10_000,
        max_retries=3,
        base_backoff_seconds=0.001,
        max_wait_seconds=1.0,
    )
    defaults.update(kwargs)
    return ResilientProvider(inner, "test", **defaults)


@pytest.mark.parametrize(
    "exc",
    [
        Boom("429 Too Many Requests"),
        Boom("RESOURCE_EXHAUSTED: quota exceeded"),
        Boom("503 Service Unavailable"),
        Boom("deadline exceeded"),
        Boom("model overloaded"),
        Boom("something", status_code=429),
        Boom("something", status_code=503),
    ],
)
def test_throttles_and_outages_are_treated_as_retryable(exc):
    assert is_transient(exc) is True


@pytest.mark.parametrize(
    "exc",
    [
        Boom("API key not valid"),
        Boom("invalid request shape"),
        Boom("permission denied", status_code=403),
        Boom("not found", status_code=404),
    ],
)
def test_a_wrong_request_is_not_retried(exc):
    """Retrying a bad key just burns the quota that is already the
    constraint."""
    assert is_transient(exc) is False


def test_a_throttled_call_succeeds_on_retry():
    inner = FlakyProvider(failures=2, exc=Boom("429 rate limit"))

    assert wrap(inner).generate("hello") == "written by the model"
    assert inner.calls == 3


def test_retries_are_bounded_and_the_error_still_surfaces():
    inner = FlakyProvider(failures=99, exc=Boom("429 rate limit"))

    with pytest.raises(Boom):
        wrap(inner, max_retries=2).generate("hello")

    assert inner.calls == 3, "one attempt plus two retries, then give up"


def test_a_permanent_error_fails_on_the_first_attempt():
    inner = FlakyProvider(failures=99, exc=Boom("API key not valid"))

    with pytest.raises(Boom):
        wrap(inner).generate("hello")

    assert inner.calls == 1


def test_embeddings_get_the_same_treatment():
    """Retrieval embeds on every chat message, so it hits the quota as
    hard as generation does."""
    inner = FlakyProvider(failures=1, exc=Boom("503 unavailable"))

    assert len(wrap(inner).embed(["a", "b"])) == 2
    assert inner.calls == 2


def test_the_provider_s_own_retry_after_wins_over_our_guess():
    assert retry_after_seconds(Boom("slow down, retry-after: 7")) == 7.0

    explicit = Boom("slow down")
    explicit.retry_after = 3
    assert retry_after_seconds(explicit) == 3.0

    assert retry_after_seconds(Boom("no hint here")) is None


def test_status_code_is_read_from_whichever_shape_the_sdk_used():
    assert status_code_of(Boom("x", status_code=429)) == 429

    class WithResponse(Exception):
        class response:  # noqa: N801
            status_code = 503

    assert status_code_of(WithResponse()) == 503
    assert status_code_of(Boom("plain")) is None


def test_the_limiter_lets_the_budget_through_and_then_holds():
    limiter = RateLimiter(requests_per_minute=3, max_wait_seconds=0.2)
    limiter._local = []

    # Three slots in the window, taken without waiting.
    for _ in range(3):
        assert limiter._try_local(1000.0) is True

    # The fourth has nothing left in that window.
    assert limiter._try_local(1000.0) is False

    # A minute later the window has rolled.
    assert limiter._try_local(1061.0) is True


def test_running_out_of_wait_budget_sends_anyway_rather_than_dropping_work():
    """A late analysis is recoverable. A skipped one is invisible."""
    limiter = RateLimiter(requests_per_minute=1, max_wait_seconds=0.05)
    limiter._try_local(__import__("time").time())

    assert limiter.acquire() is False
