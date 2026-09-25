from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from apps.backend.models import (
    AuditLog,
    DailyFeature,
    KnowledgeDocument,
    OrgSettings,
    TelemetryEvent,
    User,
)
from ml.aggregation.cohort import ABSOLUTE_MIN_COHORT
from shared.constants.data_sources import DATA_SOURCE_CATALOG
from shared.enums.data_sources import PERMANENTLY_DISABLED_SOURCES


def get_or_create_settings(db: Session, org_id: str) -> OrgSettings:
    settings = db.scalar(select(OrgSettings).where(OrgSettings.org_id == org_id))
    if settings:
        return settings
    settings = OrgSettings(org_id=org_id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def update_settings(db: Session, org_id: str, changes: dict) -> OrgSettings:
    settings = get_or_create_settings(db, org_id)

    if "aggregation_min_cohort" in changes and changes["aggregation_min_cohort"] is not None:
        # An admin may raise the privacy floor but never lower it.
        changes["aggregation_min_cohort"] = max(
            int(changes["aggregation_min_cohort"]), ABSOLUTE_MIN_COHORT
        )

    for field, value in changes.items():
        if value is not None and hasattr(settings, field):
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


def data_source_catalog() -> list[dict]:
    return [
        {
            "key": d.key.value,
            "label": d.label,
            "category": d.category,
            "default_enabled": d.default_enabled,
            "collectible": d.collectible,
            "never_collectible": d.key in PERMANENTLY_DISABLED_SOURCES,
            "retention": d.retention,
        }
        for d in DATA_SOURCE_CATALOG
    ]


def list_org_users(db: Session, org_id: str) -> list[dict]:
    from apps.backend.models import Role

    rows = db.execute(
        select(User, Role.name).join(Role, Role.id == User.role_id).where(User.org_id == org_id)
    ).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": role_name,
            "team": user.team,
            "is_active": user.is_active,
        }
        for user, role_name in sorted(rows, key=lambda r: r[0].email)
    ]


def set_user_active(db: Session, org_id: str, user_id: str, is_active: bool) -> dict:
    """Deactivation is how an employee who has left stops being analysed.
    It is scoped to the admin's own org - an admin elsewhere must not be
    able to disable this org's accounts by guessing an id."""
    user = db.get(User, user_id)
    if user is None or user.org_id != org_id:
        return {}
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "is_active": user.is_active}


def recent_audit_logs(db: Session, org_id: str, limit: int = 100) -> list[dict]:
    org_user_ids = select(User.id).where(User.org_id == org_id)
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.actor_id.in_(org_user_ids) | AuditLog.subject_user_id.in_(org_user_ids))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "subject_user_id": r.subject_user_id,
            "action": r.action,
            "resource": r.resource,
            "meta": r.meta,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def knowledge_base_summary(db: Session) -> list[dict]:
    rows = db.execute(
        select(
            KnowledgeDocument.category,
            func.count(KnowledgeDocument.id),
        ).group_by(KnowledgeDocument.category)
    ).all()
    return [{"category": category, "documents": count} for category, count in rows]


def apply_retention(db: Session, org_id: str) -> dict:
    """Deletes telemetry and daily features older than the org's retention
    window. Phase 12 makes retention a real, enforceable setting rather than
    a promise in a privacy policy."""
    settings = get_or_create_settings(db, org_id)
    cutoff = date.today() - timedelta(days=settings.retention_days)
    org_user_ids = select(User.id).where(User.org_id == org_id)

    telemetry_deleted = db.execute(
        delete(TelemetryEvent).where(
            TelemetryEvent.employee_id.in_(org_user_ids),
            TelemetryEvent.timestamp < cutoff,
        )
    ).rowcount
    features_deleted = db.execute(
        delete(DailyFeature).where(
            DailyFeature.employee_id.in_(org_user_ids),
            DailyFeature.date < cutoff,
        )
    ).rowcount
    db.commit()

    return {
        "cutoff": cutoff.isoformat(),
        "retention_days": settings.retention_days,
        "telemetry_events_deleted": telemetry_deleted,
        "daily_features_deleted": features_deleted,
    }
