import logging

from sqlalchemy.orm import Session

from agents.providers import embedding_identity, get_provider
from apps.backend.models import KnowledgeDocument
from apps.backend.repositories import knowledge_repo

logger = logging.getLogger("workwell.retrieval")


def retrieve(db: Session, query: str, top_k: int = 4, category: str | None = None) -> list[dict]:
    provider = get_provider()

    # Embedding needs the provider, so an outage costs retrieval. Returning
    # no sources degrades the answer; raising would take down the whole
    # dashboard, which is the wrong trade for a wellness tool.
    try:
        [embedding] = provider.embed([query])
    except Exception:
        logger.warning("retrieval unavailable: embedding provider failed")
        return []

    model = embedding_identity()
    results = knowledge_repo.similarity_search(
        db, embedding, top_k=top_k, category=category, embedding_model=model
    )

    if not results and knowledge_repo.count_chunks(db) > 0:
        # There is a knowledge base; none of it was embedded by the model
        # now asking. Almost always a provider switch without re-ingesting.
        logger.error(
            "knowledge base holds no chunks embedded by %s - re-run "
            "scripts/ingest_knowledge.py after changing provider or embedding model",
            model,
        )

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
