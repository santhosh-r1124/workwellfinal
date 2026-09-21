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


def _instrumented(provider: AIProvider, name: str) -> AIProvider:
    from agents.providers.instrumented import InstrumentedProvider

    return InstrumentedProvider(provider, name)
