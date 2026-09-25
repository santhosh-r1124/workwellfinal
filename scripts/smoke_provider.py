"""Prove the configured model provider actually works.

This is the one path automated tests cannot cover. The suite runs against
the deterministic local provider, and the resilience work means a wrong
request shape now degrades visibly instead of crashing - which is better
behaviour and exactly what hides a misconfiguration: every narration
quietly falls back, the UI shows an amber note nobody reads, and the
product ships a rule-based sentence where a written explanation was
promised.

So this makes the real calls, with the real key, and says plainly which
ones worked.

    python scripts/smoke_provider.py
    AI_PROVIDER=gemini GEMINI_API_KEY=... python scripts/smoke_provider.py

Exit code 0 means every configured capability answered.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.backend.core.config import get_settings  # noqa: E402

SYSTEM = (
    "You are the Context Agent for WorkWell AI. Write one cautious sentence. "
    "Never assert a diagnosis. Never mention a clinical condition."
)
PROMPT = "Candidate contexts: release period, meeting increase.\nEmployee note: (none provided)"

# The words the product must never put in front of an employee. A provider
# that ignores the system instruction is a product problem, not a config
# one, and it is worth finding out here rather than in someone's dashboard.
FORBIDDEN = ["anxiety", "depression", "burnout", "diagnos", "disorder"]


def _report(label: str, ok: bool, detail: str) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {detail}")


def main() -> int:
    settings = get_settings()
    print(f"provider: {settings.ai_provider}")
    print(f"model:    {settings.gemini_model}")
    print(f"key:      {'set' if settings.ai_configured else 'NOT SET'}\n")

    if settings.ai_provider == "gemini" and not settings.ai_configured:
        print("GEMINI_API_KEY is empty - the factory would silently hand back the")
        print("local deterministic provider, and every explanation in the product")
        print("would be a canned sentence. Set the key and run this again.")
        return 1

    from agents.providers import get_provider

    provider = get_provider()
    failures = 0

    # 1. Generation - what every narration depends on.
    started = time.perf_counter()
    try:
        text = provider.generate(PROMPT, system=SYSTEM)
        elapsed = time.perf_counter() - started
        if not text.strip():
            _report("generate", False, "returned empty text")
            failures += 1
        else:
            _report("generate", True, f"{len(text)} chars in {elapsed:.2f}s")
            print(f"        > {text[:180]}")
            leaked = [w for w in FORBIDDEN if w in text.lower()]
            if leaked:
                _report("safety wording", False, f"model produced {leaked}")
                failures += 1
            else:
                _report("safety wording", True, "no clinical language")
    except Exception as exc:
        _report("generate", False, f"{type(exc).__name__}: {exc}")
        failures += 1

    # 2. Embeddings - what the wellness knowledge base is retrieved with.
    started = time.perf_counter()
    try:
        vectors = provider.embed(["taking a real lunch break improves afternoon focus"])
        elapsed = time.perf_counter() - started
        dim = len(vectors[0]) if vectors else 0
        if dim != settings.gemini_embedding_dim:
            _report(
                "embed",
                False,
                f"returned {dim} dimensions, but the pgvector column is "
                f"{settings.gemini_embedding_dim} - retrieval would fail on insert",
            )
            failures += 1
        else:
            _report("embed", True, f"{dim} dimensions in {elapsed:.2f}s")
    except Exception as exc:
        _report("embed", False, f"{type(exc).__name__}: {exc}")
        failures += 1

    print()
    if failures:
        print(f"{failures} capability check(s) failed. The product will run, but every")
        print("explanation will fall back to its rule-based text.")
        return 1

    print("provider is answering on every path the product uses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
