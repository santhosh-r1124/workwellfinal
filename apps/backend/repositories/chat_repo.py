from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import ChatMessage, ChatSession, SafetyEvent


def latest_employee_note(db: Session, employee_id: str, within_days: int = 7) -> str | None:
    """The most recent thing the employee said about their own situation.

    An employee who explains "it's because of a release" should not have
    to explain it again tomorrow. The scheduled analysis has no human in
    the loop to ask, so it reads the last note the employee volunteered
    and passes it to the context agent exactly as the chat path does.

    Messages that tripped the safety classifier are excluded: those belong
    to the safety pipeline, which is deliberately separate, and must not
    be recycled as workplace context.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)

    flagged = select(SafetyEvent.chat_message_id).where(
        SafetyEvent.chat_message_id.is_not(None)
    )

    stmt = (
        select(ChatMessage.content)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatSession.employee_id == employee_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= cutoff,
            ChatMessage.id.not_in(flagged),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()
