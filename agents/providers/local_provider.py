import hashlib
import math

from apps.backend.core.config import get_settings


class LocalProvider:
    """Deterministic, offline stand-in for the AI provider. Used in tests and
    as a safety fallback when no Gemini key is configured, so the
    statistical pipeline (baseline, anomaly, dashboard) stays testable and
    demoable without live model access. Text is templated, not generated;
    embeddings are a normalized hash projection, not semantically meaningful."""

    # Nothing here writes a sentence. Callers use this to tell an employee
    # "no explanation is available" instead of showing them the string
    # below, which is a note to whoever deployed this.
    generates_text = False

    def generate(self, prompt: str, system: str | None = None) -> str:
        return (
            "[local-mode explanation] The statistical evidence above was computed "
            "directly by the analysis pipeline. Configure GEMINI_API_KEY to enable "
            "natural-language explanations from the wellness agent."
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        dim = get_settings().gemini_embedding_dim
        return [self._hash_embedding(t, dim) for t in texts]

    @staticmethod
    def _hash_embedding(text: str, dim: int) -> list[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        vector = [math.sin(seed[i % len(seed)] + i) for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
