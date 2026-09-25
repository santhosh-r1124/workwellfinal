"""Switching embedding model must not silently corrupt retrieval.

Vectors from two models are not comparable, and comparing them does not
fail - pgvector happily ranks them and returns a confident top_k of the
wrong chunks. That is the single worst way for this to break, because the
advice keeps flowing and just stops being relevant.
"""

from apps.backend.repositories import knowledge_repo
from apps.backend.services import admin_service


def _chunk(db_session, model: str, content: str):
    doc = knowledge_repo.create_document(
        db_session, title=content[:20], source_url=None, category="recovery"
    )
    return knowledge_repo.create_chunk(
        db_session,
        document_id=doc.id,
        content=content,
        meta={},
        embedding=[0.1] * 768,
        embedding_model=model,
    )


def test_retrieval_ignores_chunks_from_another_model(db_session):
    _chunk(db_session, "local:hash-projection", "embedded by the offline stand-in")

    results = knowledge_repo.similarity_search(
        db_session, [0.1] * 768, embedding_model="gemini:text-embedding-004"
    )

    assert results == [], "a chunk from another vector space must not be returned"


def test_retrieval_finds_chunks_from_the_current_model(db_session):
    _chunk(db_session, "gemini:text-embedding-004", "embedded by the live model")

    results = knowledge_repo.similarity_search(
        db_session, [0.1] * 768, embedding_model="gemini:text-embedding-004"
    )

    assert len(results) == 1


def test_admin_can_see_that_the_knowledge_base_needs_re_ingesting(db_session, monkeypatch):
    from apps.backend.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "a-key")

    _chunk(db_session, "local:hash-projection", "stale")

    health = admin_service.knowledge_base_health(db_session)

    assert health["ready"] is False
    assert health["usable_chunks"] == 0
    assert health["stale_chunks"] == 1
    assert health["stale_models"] == ["local:hash-projection"]
    assert "ingest_knowledge" in health["hint"]


def test_re_ingesting_replaces_rather_than_duplicates(db_session, tmp_path):
    """Re-embedding is the documented recovery from a provider switch. It
    used to leave the broken copy in place beside the new one."""
    from rag.ingestion.pipeline import ingest_knowledge_base

    category = tmp_path / "recovery"
    category.mkdir()
    (category / "rest.md").write_text("# Rest\n\nTaking a real lunch break improves focus.\n")

    first = ingest_knowledge_base(db_session, root=tmp_path)
    second = ingest_knowledge_base(db_session, root=tmp_path)

    assert first == second
    assert knowledge_repo.count_chunks(db_session) == second
