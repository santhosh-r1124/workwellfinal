from sqlalchemy.orm import Session

from agents.narration import safe_generate
from agents.providers import get_provider
from rag.retrieval.retriever import retrieve

SYSTEM_PROMPT = (
    "You are the WorkWell Wellness RAG assistant. Answer the employee's question using ONLY the "
    "provided source excerpts. This is general workplace wellness guidance, not medical advice. "
    "If the excerpts don't cover the question, say so plainly rather than guessing. Keep answers "
    "under 150 words."
)


def answer_query(db: Session, query: str, category: str | None, top_k: int = 4) -> dict:
    sources = retrieve(db, query, top_k=top_k, category=category)
    if not sources:
        return {"answer": "No matching guidance was found in the knowledge base yet.", "sources": []}

    provider = get_provider()
    context = "\n\n".join(f"[{i + 1}] {s['title']}: {s['content']}" for i, s in enumerate(sources))
    prompt = f"Question: {query}\n\nSource excerpts:\n{context}"

    # Without the model we can still hand back the retrieved guidance, which
    # is the part that was actually vetted.
    fallback = "Couldn't summarise right now. The most relevant guidance is: " + "; ".join(
        s["title"] for s in sources
    )
    answer, _ = safe_generate(provider, prompt, SYSTEM_PROMPT, fallback)

    return {
        "answer": answer,
        "sources": [{"title": s["title"], "url": s["url"], "category": s["category"]} for s in sources],
    }
