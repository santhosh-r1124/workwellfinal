"""The employee-facing assistant.

Chat explains an analysis; it does not produce one. That split is what
takes the agent pipeline off the request path: previously every message
recomputed 90 days of baselines and made three model calls before the
assistant could answer, which put the product's slowest operation in front
of its most latency-sensitive surface - and meant the chat could disagree
with the dashboard the employee was looking at, because each recomputed
independently.

Now the stored run is the single source of truth for both. A message adds
exactly one thing the stored run does not have: whatever the employee just
said about their own situation. So the chat re-runs only the two steps
that consume it - context, then the recommendation grounded in retrieved
guidance - and never writes a new analysis or a new nudge.
"""

import logging

from sqlalchemy.orm import Session

from agents import context_agent, safety_agent, wellness_agent
from agents.narration import generates_text
from agents.providers import get_provider
from apps.backend.models import ChatMessage, ChatSession
from apps.backend.services import analysis_service

logger = logging.getLogger("workwell.chat")

QUEUED_REPLY = (
    "I'm still putting your analysis together - it needs a couple of weeks of your own "
    "history before it can tell your normal apart from a change. Check back shortly."
)

UNAVAILABLE_REPLY = (
    "I can't reach the analysis pipeline right now. Your dashboard still shows "
    "what changed in your work pattern."
)


def get_or_create_session(db: Session, employee_id: str, session_id: str | None) -> ChatSession:
    if session_id:
        existing = db.get(ChatSession, session_id)
        if existing and existing.employee_id == employee_id:
            return existing
    session = ChatSession(employee_id=employee_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _answer_from_analysis(db: Session, employee_id: str, message: str) -> tuple[str, list[dict], bool]:
    analysis = analysis_service.current_analysis(db, employee_id)

    if analysis is None:
        return QUEUED_REPLY, [], False

    # The inline path returns the orchestrator's own early exits verbatim.
    if analysis.get("state") in ("NO_CONSENT", "INSUFFICIENT_DATA"):
        return analysis["message"], [], False

    pattern = analysis.get("pattern") or {}
    stored_wellness = analysis.get("wellness") or {}

    if not pattern:
        # A stored run whose pattern row has aged out of retention. The
        # recommendation it produced is still the honest answer.
        return (
            stored_wellness.get("recommendation") or QUEUED_REPLY,
            stored_wellness.get("sources", []),
            False,
        )

    context = context_agent.analyze_context(pattern, message)
    wellness = wellness_agent.build_recommendation(
        db, pattern, context, analysis.get("intervention") or {}, get_provider()
    )

    degraded = not (context.get("narrated", True) and wellness.get("narrated", True))
    return wellness["recommendation"], wellness.get("sources", []), degraded


def _degraded_reason(degraded: bool) -> str | None:
    """Both situations produce evidence-derived text instead of prose, but
    only one of them is a fault. Telling someone the model was unreachable
    on an install that was deliberately run without one sends them to debug
    nothing."""
    if not degraded:
        return None
    return "not_configured" if not generates_text(get_provider()) else "unreachable"


def handle_message(db: Session, employee_id: str, session_id: str | None, message: str) -> dict:
    session = get_or_create_session(db, employee_id, session_id)

    user_msg = ChatMessage(session_id=session.id, role="user", content=message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Safety runs independently of the main agent pipeline (Phase 10) and is
    # checked before anything else touches this message.
    safety_result = safety_agent.check_message(db, employee_id, user_msg.id, message)

    if safety_result["flagged"]:
        # The safety path is deterministic and never depends on the model,
        # so it answers even during a provider outage.
        reply, sources, degraded = safety_result["response"], [], False
    else:
        try:
            reply, sources, degraded = _answer_from_analysis(db, employee_id, message)
        except Exception:
            logger.exception("could not answer from the stored analysis")
            reply, sources, degraded = UNAVAILABLE_REPLY, [], True

    assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()

    return {
        "session_id": session.id,
        "reply": reply,
        "sources": sources,
        "safety_flagged": safety_result["flagged"],
        "degraded": degraded,
        "degraded_reason": _degraded_reason(degraded),
    }
