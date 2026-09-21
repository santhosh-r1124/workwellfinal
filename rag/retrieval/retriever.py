from sqlalchemy.orm import Session

from agents.providers import get_provider
from apps.backend.models import KnowledgeDocument
from apps.backend.repositories import knowledge_repo


def retrieve(db: Session, query: str, top_k: int = 4, category: str | None = None) -> list[dict]:
    provider = get_provider()
    [embedding] = provider.embed([query])
    results = knowledge_repo.similarity_search(db, embedding, top_k=top_k, category=category)

    output = []
    for chunk, distance in results:
        document = db.get(KnowledgeDocument, chunk.document_id)
        output.append(
            {
                "content": chunk.content,
                "title": document.title if document else "Unknown",
                "url": document.source_url if document else None,
                "category": document.category if document else None,
                "distance": float(distance),
            }
        )
    return output
