from sqlalchemy.orm import Session

from safety import classifier, escalation, policy
from shared.enums.safety import SafetySeverity


def check_message(db: Session, employee_id: str, chat_message_id: str | None, text: str) -> dict:
    """Runs independently of agents.orchestrator (Phase 10): normal
    workplace telemetry never feeds this, only explicit chat content."""
    classification = classifier.classify(text)

    if classification["severity"] == SafetySeverity.NONE.value:
        return {"flagged": False}

    action = policy.action_for(classification["severity"])
    escalation.record_safety_event(db, employee_id, chat_message_id, classification, action)

    return {
        "flagged": True,
        "severity": classification["severity"],
        "response": policy.response_for(classification["severity"]),
    }
