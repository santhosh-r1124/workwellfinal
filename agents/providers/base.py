from typing import Protocol


class AIProvider(Protocol):
    """A text/embedding backend.

    `generates_text` is the honest answer to "did a language model write
    this?". The offline stand-in answers False: its `generate` returns a
    fixed string, and passing that to an employee as an explanation is the
    thing this product must never do. Providers that omit the attribute are
    treated as generating - see `narration.generates_text`.
    """

    generates_text: bool

    def generate(self, prompt: str, system: str | None = None) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
