from sqlalchemy.orm import Session

from apps.backend.models import SafetyEvent


def record_safety_event(
    db: Session, employee_id: str, chat_message_id: str | None, classification: dict, action_taken: str
) -> SafetyEvent:
    row = SafetyEvent(
        employee_id=employee_id,
        chat_message_id=chat_message_id,
        category=classification.get("category") or "none",
        severity=classification["severity"],
        action_taken=action_taken,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
