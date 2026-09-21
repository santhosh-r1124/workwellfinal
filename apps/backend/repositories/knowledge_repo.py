from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import KnowledgeChunk, KnowledgeDocument


def create_document(db: Session, title: str, source_url: str | None, category: str) -> KnowledgeDocument:
    doc = KnowledgeDocument(title=title, source_url=source_url, category=category)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def create_chunk(db: Session, document_id: str, content: str, meta: dict, embedding: list[float]) -> KnowledgeChunk:
    chunk = KnowledgeChunk(document_id=document_id, content=content, meta=meta, embedding=embedding)
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def similarity_search(
    db: Session, query_embedding: list[float], top_k: int = 4, category: str | None = None
) -> list[tuple[KnowledgeChunk, float]]:
    stmt = select(
        KnowledgeChunk, KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance")
    )
    if category:
        stmt = stmt.join(KnowledgeDocument).where(KnowledgeDocument.category == category)
    stmt = stmt.order_by("distance").limit(top_k)
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def count_chunks(db: Session) -> int:
    return len(list(db.scalars(select(KnowledgeChunk.id))))
