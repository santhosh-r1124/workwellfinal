"""Embed the wellness knowledge base into pgvector.

Run this whenever the embedding model changes - which includes the first
time you set a real GEMINI_API_KEY, because everything ingested before
that was embedded by the offline stand-in, whose vectors are a hash
projection with no semantic meaning. Retrieval will not error on them; it
will return the wrong guidance, confidently.

    python scripts/ingest_knowledge.py
    python scripts/ingest_knowledge.py --append   # add without replacing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.providers import embedding_identity  # noqa: E402
from apps.backend.core.database import session_scope  # noqa: E402
from apps.backend.repositories import knowledge_repo  # noqa: E402
from rag.ingestion.pipeline import ingest_knowledge_base  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--append",
        action="store_true",
        help="keep what is already stored instead of replacing it",
    )
    args = parser.parse_args()

    model = embedding_identity()
    print(f"embedding with: {model}")

    if model.startswith("local:"):
        print(
            "\nWARNING: this is the offline stand-in, not a real embedding model.\n"
            "Its vectors are a hash projection - retrieval will return chunks, but\n"
            "they will not be the relevant ones. Set GEMINI_API_KEY and AI_PROVIDER=gemini,\n"
            "then run this again.\n"
        )

    with session_scope() as db:
        before = knowledge_repo.embedding_models_present(db)
        if before:
            print("currently stored:")
            for name, count in sorted(before.items()):
                print(f"  {name}: {count} chunks")

        chunks = ingest_knowledge_base(db, replace=not args.append)
        print(f"\ningested {chunks} chunks as {model}")

        after = knowledge_repo.embedding_models_present(db)
        stale = {k: v for k, v in after.items() if k != model}
        if stale:
            print("\nstill holding chunks from another model, which retrieval will ignore:")
            for name, count in sorted(stale.items()):
                print(f"  {name}: {count} chunks")
            print("Re-run without --append to clear them.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
