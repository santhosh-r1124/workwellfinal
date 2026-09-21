from functools import lru_cache

from agents.providers.base import AIProvider
from apps.backend.core.config import get_settings


@lru_cache
def get_provider() -> AIProvider:
    settings = get_settings()

    if settings.ai_provider == "gemini" and settings.ai_configured:
        from agents.providers.gemini_provider import GeminiProvider

        return GeminiProvider()

    if settings.ai_provider == "openai":
        from agents.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()

    from agents.providers.local_provider import LocalProvider

    return LocalProvider()
