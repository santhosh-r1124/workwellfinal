import time
from typing import Callable

from agents.providers.base import AIProvider
from apps.backend.core.observability import record_llm_call


class InstrumentedProvider:
    """Wraps any AIProvider to record call volume, latency and failures
    (Phase 19). Kept as a wrapper so individual providers stay unaware of
    metrics, and so LLM cost/latency stays observable regardless of vendor.

    Only the provider name and timing are recorded - never prompt or
    response content, which would put employee context into operational
    telemetry.
    """

    def __init__(self, inner: AIProvider, name: str) -> None:
        self._inner = inner
        self._name = name

    def _timed(self, fn: Callable, *args, **kwargs):
        start = time.perf_counter()
        failed = False
        try:
            return fn(*args, **kwargs)
        except Exception:
            failed = True
            raise
        finally:
            record_llm_call(self._name, time.perf_counter() - start, failed=failed)

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._timed(self._inner.generate, prompt, system=system)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._timed(self._inner.embed, texts)
