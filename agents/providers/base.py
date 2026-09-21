from typing import Protocol


class AIProvider(Protocol):
    def generate(self, prompt: str, system: str | None = None) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
