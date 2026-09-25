from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.backend.models import KnowledgeChunk, KnowledgeDocument


def create_document(db: Session, title: str, source_url: str | None, category: str) -> KnowledgeDocument:
    doc = KnowledgeDocument(title=title, source_url=source_url, category=category)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def create_chunk(
    db: Session,
    document_id: str,
    content: str,
    meta: dict,
    embedding: list[float],
    embedding_model: str,
) -> KnowledgeChunk:
    chunk = KnowledgeChunk(
        document_id=document_id,
        content=content,
        meta=meta,
        embedding=embedding,
        embedding_model=embedding_model,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def similarity_search(
    db: Session,
    query_embedding: list[float],
    top_k: int = 4,
    category: str | None = None,
    embedding_model: str | None = None,
) -> list[tuple[KnowledgeChunk, float]]:
    """Restricted to one model's vector space.

    Without the filter, a knowledge base embedded by a previous provider
    still returns a full top_k against the new provider's query vector -
    ranked by a distance that means nothing. Empty results are the correct
    answer there, and the caller says so out loud.
    """
    stmt = select(
        KnowledgeChunk, KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance")
    )
    if embedding_model:
        stmt = stmt.where(KnowledgeChunk.embedding_model == embedding_model)
    if category:
        stmt = stmt.join(KnowledgeDocument).where(KnowledgeDocument.category == category)
    stmt = stmt.order_by("distance").limit(top_k)
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def count_chunks(db: Session, embedding_model: str | None = None) -> int:
    stmt = select(func.count(KnowledgeChunk.id))
    if embedding_model:
        stmt = stmt.where(KnowledgeChunk.embedding_model == embedding_model)
    return int(db.scalar(stmt) or 0)


def embedding_models_present(db: Session) -> dict[str, int]:
    """What the stored knowledge base was embedded with, and how much of
    each. An admin screen showing this is how a provider switch becomes
    visible before someone notices the advice has gone strange."""
    rows = db.execute(
        select(KnowledgeChunk.embedding_model, func.count(KnowledgeChunk.id)).group_by(
            KnowledgeChunk.embedding_model
        )
    ).all()
    return {model: count for model, count in rows}


def delete_all_knowledge(db: Session) -> int:
    """Re-ingesting must replace, not accumulate: the previous behaviour
    duplicated every document on each run, which made recovering from a
    provider switch add a second broken copy."""
    removed = db.query(KnowledgeChunk).delete()
    db.query(KnowledgeDocument).delete()
    db.commit()
    return removed
