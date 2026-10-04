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
        self._models = [settings.gemini_model] + [
            m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()
        ]
        self._embedding_model = settings.gemini_embedding_model
        self._embedding_dim = settings.gemini_embedding_dim

    def generate(self, prompt: str, system: str | None = None) -> str:
        config = types.GenerateContentConfig(system_instruction=system) if system else None
        last_error: Exception | None = None
        for model in self._models:
            try:
                response = self._client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                return (response.text or "").strip()
            except Exception as exc:
                # A spent quota or an overloaded model moves on to the next
                # one. A bad key or a malformed request fails the same way
                # on all of them, so those are raised straight away.
                if not any(m in str(exc) for m in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
                    raise
                last_error = exc
        raise last_error

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Newer embedding models default to more dimensions than the
        # knowledge_chunks column holds; ask for exactly what it stores.
        result = self._client.models.embed_content(
            model=self._embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=self._embedding_dim),
        )
        return [list(e.values) for e in result.embeddings]
