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


def safe_generate(
    provider: AIProvider, prompt: str, system: str | None, fallback: str
) -> tuple[str, bool]:
    """Returns (text, narrated). `narrated` is False when the model could not
    be reached and `fallback` is being shown instead."""
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
