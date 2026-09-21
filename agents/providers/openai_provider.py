class OpenAIProvider:
    """Phase 15 optional provider slot. The MVP ships Gemini-only (Phase 14)
    to keep setup to a single API key; this stub documents the extension
    point without half-implementing a second vendor integration."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "OpenAIProvider is a Phase 15 extension point, not implemented in the MVP. "
            "Set AI_PROVIDER=gemini."
        )

    def generate(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
