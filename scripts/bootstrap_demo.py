"""First-start data for a DEMO_MODE deployment. Idempotent: imports the
employee dataset only when no imported employees exist, and embeds the
wellness knowledge base only when it is empty. Run after migrations."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from apps.backend.core.config import get_settings  # noqa: E402
from apps.backend.core.database import SessionLocal  # noqa: E402
from apps.backend.models import KnowledgeChunk, User  # noqa: E402


def main() -> None:
    if not get_settings().demo_mode:
        print("bootstrap: DEMO_MODE is off, nothing to do")
        return

    db = SessionLocal()
    try:
        imported = db.scalar(select(func.count(User.id)).where(User.id.like("emp_%")))
        chunks = db.scalar(select(func.count(KnowledgeChunk.id)))
        stored_models = set(db.scalars(select(KnowledgeChunk.embedding_model).distinct()))
    finally:
        db.close()

    if not imported:
        from scripts.import_employee_data import DEFAULT_CSV, import_csv

        import_csv(DEFAULT_CSV)
    else:
        print(f"bootstrap: {imported} employees already present")

    from agents.providers import embedding_identity

    # Vectors from two embedding models are not comparable; switching the
    # provider (e.g. adding a Gemini key) means re-embedding everything.
    if not chunks or stored_models != {embedding_identity()}:
        from rag.ingestion.pipeline import ingest_knowledge_base

        db = SessionLocal()
        try:
            print("bootstrap: knowledge chunks ingested:", ingest_knowledge_base(db))
        finally:
            db.close()


if __name__ == "__main__":
    main()
