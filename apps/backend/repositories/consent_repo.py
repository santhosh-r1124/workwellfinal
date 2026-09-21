from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import Consent, ConsentEvent


def get_consent(db: Session, user_id: str, source: str) -> Consent | None:
    return db.scalar(
        select(Consent).where(Consent.user_id == user_id, Consent.source == source)
    )


def list_consents(db: Session, user_id: str) -> list[Consent]:
    return list(db.scalars(select(Consent).where(Consent.user_id == user_id)))


def list_consent_events(db: Session, user_id: str) -> list[ConsentEvent]:
    return list(
        db.scalars(
            select(ConsentEvent)
            .where(ConsentEvent.user_id == user_id)
            .order_by(ConsentEvent.created_at.desc())
        )
    )
