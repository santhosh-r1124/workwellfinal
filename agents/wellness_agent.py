from sqlalchemy.orm import Session

from agents.providers.base import AIProvider
from rag.retrieval.retriever import retrieve

SYSTEM_PROMPT = (
    "You are the Wellness Agent for WorkWell AI. You are given observed statistical changes in "
    "an employee's work pattern, a cautious possible workplace context, and short excerpts of "
    "trusted wellness guidance. Write a brief, warm, non-clinical recommendation (2-4 sentences): "
    "state what was observed, optionally note the context may explain part of it, and offer one "
    "concrete, low-friction suggestion drawn from the guidance. Never diagnose. Never label the "
    "employee with a clinical term such as anxiety, depression, or burnout."
)


def describe_signal(signal: dict) -> str:
    """Signals centred near zero carry their unit, because a percentage of a
    near-zero centre is a meaningless number to hand an LLM - or a person."""
    name = signal["name"].replace("_", " ")
    change = signal["change"]
    days = signal["anomalous_days"]
    kind = signal.get("change_kind", "relative")

    if kind == "spread":
        amount = f"{change:+.1f}x its usual variation"
    elif kind == "absolute":
        amount = f"{change:+.2f}"
    else:
        amount = f"{change:+.0%}"

    return f"{name} changed by {amount} over {days} days"


def build_recommendation(
    db: Session, pattern: dict, context: dict, intervention: dict, provider: AIProvider
) -> dict:
    query_terms = " ".join(
        filter(None, [intervention.get("type", ""), *context.get("likely_context", [])])
    ) or "workplace wellness"
    sources = retrieve(db, query_terms, top_k=3)

    observations = [describe_signal(s) for s in pattern.get("signals", [])]

    guidance_block = "\n".join(f"- {s['content'][:300]}" for s in sources) or "(no matching guidance found)"
    prompt = (
        f"Observed: {'; '.join(observations) or 'no sustained change'}.\n"
        f"Possible context: {', '.join(context.get('likely_context', [])) or 'none identified'}.\n"
        f"Guidance excerpts:\n{guidance_block}"
    )
    recommendation = provider.generate(prompt, system=SYSTEM_PROMPT)

    return {
        "observations": observations,
        "context_note": context.get("explanation"),
        "recommendation": recommendation,
        "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
    }
