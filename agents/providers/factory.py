from functools import lru_cache

from agents.providers.base import AIProvider
from apps.backend.core.config import get_settings


@lru_cache
def get_provider() -> AIProvider:
    settings = get_settings()

    if settings.ai_provider == "gemini" and settings.ai_configured:
        from agents.providers.gemini_provider import GeminiProvider

        return _instrumented(GeminiProvider(), "gemini")

    if settings.ai_provider == "openai":
        from agents.providers.openai_provider import OpenAIProvider

        return _instrumented(OpenAIProvider(), "openai")

    from agents.providers.local_provider import LocalProvider

    return _instrumented(LocalProvider(), "local")


def embedding_identity() -> str:
    """Which model's vector space the embeddings live in.

    Cosine distance between vectors from two different models is a number,
    not a similarity - the search still returns its top_k, ranked by
    nonsense. Recording this alongside each stored embedding is what turns
    "switched provider, retrieval quietly went wrong" into something the
    system can see.
    """
    settings = get_settings()

    if settings.ai_provider == "gemini" and settings.ai_configured:
        return f"gemini:{settings.gemini_embedding_model}"
    if settings.ai_provider == "openai":
        return "openai:unconfigured"
    return "local:hash-projection"


def _instrumented(provider: AIProvider, name: str) -> AIProvider:
    """Order matters. Resilience sits inside, so retries and throttle
    waits happen before the metric is recorded - one logical call is one
    entry in `workwell_llm_calls_total`, with its real end-to-end latency,
    and the retries it took are counted separately."""
    from agents.providers.instrumented import InstrumentedProvider
    from agents.providers.resilient import ResilientProvider

    settings = get_settings()

    if name == "local":
        # Nothing to pace: no network, no quota.
        return InstrumentedProvider(provider, name)

    resilient = ResilientProvider(
        provider,
        name,
        requests_per_minute=settings.llm_requests_per_minute,
        max_retries=settings.llm_max_retries,
        base_backoff_seconds=settings.llm_retry_base_seconds,
        max_wait_seconds=settings.llm_max_wait_seconds,
    )
    return InstrumentedProvider(resilient, name)
