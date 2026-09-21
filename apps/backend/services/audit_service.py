from sqlalchemy.orm import Session

from apps.backend.models import AuditLog


def record(
    db: Session,
    actor_id: str | None,
    subject_user_id: str | None,
    action: str,
    resource: str,
    meta: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor_id,
        subject_user_id=subject_user_id,
        action=action,
        resource=resource,
        meta=meta or {},
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
