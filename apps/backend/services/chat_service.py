import logging

from sqlalchemy.orm import Session

from agents import safety_agent
from agents.orchestrator import run_orchestration
from apps.backend.models import ChatMessage, ChatSession

logger = logging.getLogger("workwell.chat")


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


def handle_message(db: Session, employee_id: str, session_id: str | None, message: str) -> dict:
    session = get_or_create_session(db, employee_id, session_id)

    user_msg = ChatMessage(session_id=session.id, role="user", content=message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Safety runs independently of the main agent pipeline (Phase 10) and is
    # checked before anything else touches this message.
    safety_result = safety_agent.check_message(db, employee_id, user_msg.id, message)

    degraded = False

    if safety_result["flagged"]:
        # The safety path is deterministic and never depends on the model,
        # so it answers even during a provider outage.
        reply = safety_result["response"]
        sources: list[dict] = []
    else:
        try:
            result = run_orchestration(db, employee_id, employee_note=message)
        except Exception:
            logger.exception("orchestration failed for chat message")
            result = None

        if result is None:
            reply = (
                "I can't reach the analysis pipeline right now. Your dashboard still shows "
                "what changed in your work pattern."
            )
            sources = []
            degraded = True
        elif result.get("state") in ("NO_CONSENT", "INSUFFICIENT_DATA"):
            reply = result["message"]
            sources = []
        else:
            reply = result["wellness"]["recommendation"]
            sources = result["wellness"].get("sources", [])
            degraded = result.get("narrative_degraded", False)

    assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()

    return {
        "session_id": session.id,
        "reply": reply,
        "sources": sources,
        "safety_flagged": safety_result["flagged"],
        "degraded": degraded,
    }
