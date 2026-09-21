from agents.providers.base import AIProvider


def embed_chunks(chunks: list[str], provider: AIProvider) -> list[list[float]]:
    return provider.embed(chunks)
