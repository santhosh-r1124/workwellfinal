"""Narration is the optional layer, not the load-bearing one.

Every number this product shows an employee is computed by `ml/`. The model
only puts those numbers into sentences. So a provider outage, a revoked key
or a changed response shape must not take the evidence down with it: the
dashboard should still say what changed and by how much, and only lose the
prose.

`safe_generate` is therefore the single call site for model text. It never
raises, it records the failure as a metric, and it reports whether the
narration actually happened so callers can tell the employee the difference
between "nothing to say" and "couldn't reach the model".
"""

import logging

from agents.providers.base import AIProvider

logger = logging.getLogger("workwell.narration")


def generates_text(provider: AIProvider) -> bool:
    """Whether this provider actually writes sentences.

    The offline stand-in does not: it returns one fixed string. A provider
    that does not declare the attribute is assumed to generate, so a new
    vendor integration is never silently treated as a stand-in.
    """
    return bool(getattr(provider, "generates_text", True))


def safe_generate(
    provider: AIProvider, prompt: str, system: str | None, fallback: str
) -> tuple[str, bool]:
    """Returns (text, narrated). `narrated` is False when no model wrote the
    text and `fallback` - which is built from the measured evidence - is
    being shown instead."""
    if not generates_text(provider):
        # Without this, running with no key configured showed employees the
        # stand-in's own string ("[local-mode explanation] ... configure
        # GEMINI_API_KEY"), marked as a successful narration. That is a
        # note to whoever deployed this, presented as an explanation of
        # someone's work pattern.
        return fallback, False

    try:
        text = provider.generate(prompt, system=system)
    except Exception as exc:
        # InstrumentedProvider already counted this against the failure
        # metric; log without the prompt, which carries employee context.
        logger.warning("narration unavailable: %s", type(exc).__name__)
        return fallback, False

    if not text or not text.strip():
        return fallback, False
    return text.strip(), True
