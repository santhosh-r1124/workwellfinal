from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_db, require_role
from apps.backend.models import User
from apps.backend.services import (
    admin_service,
    audit_service,
    integration_service,
    onboarding_service,
)
from shared.enums.roles import RoleName

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_role(RoleName.ADMIN.value)


class OrgSettingsOut(BaseModel):
    org_id: str
    retention_days: int
    aggregation_min_cohort: int
    interventions_enabled: bool
    model_name: str | None
    disabled_sources: list[str]
    allowed_integrations: list[str]

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class OrgSettingsUpdate(BaseModel):
    retention_days: int | None = Field(default=None, ge=7, le=3650)
    aggregation_min_cohort: int | None = Field(default=None, ge=1, le=1000)
    interventions_enabled: bool | None = None
    model_name: str | None = None
    disabled_sources: list[str] | None = None
    allowed_integrations: list[str] | None = None

    model_config = {"protected_namespaces": ()}


@router.get("/settings", response_model=OrgSettingsOut)
def get_settings(user: User = Depends(_admin_only), db: Session = Depends(get_db)):
    return admin_service.get_or_create_settings(db, user.org_id)


@router.patch("/settings", response_model=OrgSettingsOut)
def update_settings(
    payload: OrgSettingsUpdate, user: User = Depends(_admin_only), db: Session = Depends(get_db)
):
    settings = admin_service.update_settings(db, user.org_id, payload.model_dump(exclude_unset=True))
    audit_service.record(
        db,
        actor_id=user.id,
        subject_user_id=None,
        action="admin.settings_update",
        resource=f"org_settings:{user.org_id}",
        meta=payload.model_dump(exclude_unset=True),
    )
    return settings


@router.get("/data-sources")
def data_sources(_user: User = Depends(_admin_only)):
    return {"data_sources": admin_service.data_source_catalog()}


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    team: str | None
    is_active: bool


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserCreate(BaseModel):
    email: str = Field(max_length=200)
    full_name: str = Field(default="", max_length=200)
    role: str = Field(default="employee")
    team: str | None = Field(default=None, max_length=100)


class UserCreated(BaseModel):
    id: str
    email: str
    role: str
    password: str = Field(
        description="Shown once and never stored in recoverable form. Hand it over; "
        "they change it at Settings."
    )


@router.post("/users", response_model=UserCreated, status_code=201)
def create_user(
    payload: UserCreate, user: User = Depends(_admin_only), db: Session = Depends(get_db)
):
    """Add a colleague to this organisation.

    A generated one-time password rather than an invite email, because
    email delivery is optional in this product and an onboarding path
    that silently depends on SMTP being configured is worse than one that
    hands you a string. The same shape as a device token: shown once,
    replaced by the recipient.
    """
    try:
        person, password = onboarding_service.create_person(
            db,
            org_id=user.org_id,
            email=payload.email,
            full_name=payload.full_name,
            role_name=payload.role,
            team=payload.team,
        )
    except onboarding_service.OnboardingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    audit_service.record(
        db,
        actor_id=user.id,
        subject_user_id=person.id,
        action="admin.user_created",
        resource=f"user:{person.id}",
        # The password never reaches the audit log.
        meta={"role": payload.role, "team": payload.team},
    )

    return UserCreated(id=person.id, email=person.email, role=payload.role, password=password)


@router.get("/users")
def list_users(user: User = Depends(_admin_only), db: Session = Depends(get_db)):
    return {"users": admin_service.list_org_users(db, user.org_id)}


@router.patch("/users/{user_id}")
def set_user_active(
    user_id: str,
    payload: UserActiveUpdate,
    user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    if user_id == user.id and not payload.is_active:
        # Locking the last admin out of their own org is not a recoverable
        # state through the product; it needs a database.
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    result = admin_service.set_user_active(db, user.org_id, user_id, payload.is_active)
    if not result:
        raise HTTPException(status_code=404, detail="User not found in your organization")

    audit_service.record(
        db,
        actor_id=user.id,
        subject_user_id=user_id,
        action="admin.user_activated" if payload.is_active else "admin.user_deactivated",
        resource=f"user:{user_id}",
        meta={"is_active": payload.is_active},
    )
    return result


@router.get("/audit-logs")
def audit_logs(user: User = Depends(_admin_only), db: Session = Depends(get_db), limit: int = 100):
    return {"logs": admin_service.recent_audit_logs(db, user.org_id, limit=min(limit, 500))}


@router.get("/integrations")
def integrations(user: User = Depends(_admin_only), db: Session = Depends(get_db)):
    """Connectors the build knows about. `implemented: false` means the
    connector is declared with its required OAuth config but has no client
    yet - surfaced explicitly so a vendor integration never looks configured
    when it isn't. `allowed: false` means this org's allowlist excludes it."""
    return {"connectors": integration_service.list_connectors(db, user.org_id)}


@router.get("/knowledge-base")
def knowledge_base(_user: User = Depends(_admin_only), db: Session = Depends(get_db)):
    return {
        "categories": admin_service.knowledge_base_summary(db),
        # Surfaced because a provider switch without re-ingesting breaks
        # retrieval silently rather than loudly.
        "embeddings": admin_service.knowledge_base_health(db),
    }


@router.post("/retention/apply")
def apply_retention(user: User = Depends(_admin_only), db: Session = Depends(get_db)):
    result = admin_service.apply_retention(db, user.org_id)
    audit_service.record(
        db,
        actor_id=user.id,
        subject_user_id=None,
        action="admin.retention_applied",
        resource=f"org:{user.org_id}",
        meta=result,
    )
    return result
