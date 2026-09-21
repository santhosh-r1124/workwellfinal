from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_db, require_role
from apps.backend.models import User
from apps.backend.services import admin_service, audit_service
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


@router.get("/audit-logs")
def audit_logs(user: User = Depends(_admin_only), db: Session = Depends(get_db), limit: int = 100):
    return {"logs": admin_service.recent_audit_logs(db, user.org_id, limit=min(limit, 500))}


@router.get("/knowledge-base")
def knowledge_base(_user: User = Depends(_admin_only), db: Session = Depends(get_db)):
    return {"categories": admin_service.knowledge_base_summary(db)}


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
