from google import genai
from google.genai import types

from apps.backend.core.config import get_settings


class GeminiProvider:
    """Wraps the Gemini API behind the AIProvider interface. This is the only
    provider the MVP ships enabled (Phase 14); OpenAI/local are available
    behind the same interface (Phase 15) so the app never depends on one
    vendor at the call-site level."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._embedding_model = settings.gemini_embedding_model

    def generate(self, prompt: str, system: str | None = None) -> str:
        config = types.GenerateContentConfig(system_instruction=system) if system else None
        response = self._client.models.generate_content(
            model=self._model, contents=prompt, config=config
        )
        return (response.text or "").strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(model=self._embedding_model, contents=texts)
        return [list(e.values) for e in result.embeddings]
