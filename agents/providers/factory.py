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
    from agents.providers.instrumented import InstrumentedProvider

    return InstrumentedProvider(provider, name)
