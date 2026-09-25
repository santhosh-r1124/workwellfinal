"""Employee self-service endpoints.

Every route here acts on the authenticated caller. There is deliberately no
employee_id in any path or body: it removes a whole class of IDOR mistakes,
and it matches the product rule that this data belongs to the person it is
about.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.models import SelfReport, User
from apps.backend.repositories import agent_repo, telemetry_repo
from apps.backend.services import (
    analysis_service,
    connector_service,
    device_service,
    telemetry_service,
)
from shared.enums.intervention import InterventionStatus

router = APIRouter(prefix="/me", tags=["me"])


class InterventionOut(BaseModel):
    id: str
    type: str
    message: str
    status: str
    employee_response: str | None
    created_at: str


class InterventionResponseIn(BaseModel):
    status: str
    response: str | None = None


class FeedbackIn(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class SelfReportIn(BaseModel):
    stress: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    recovery: int = Field(ge=1, le=5)
    note: str | None = None
    date: str | None = None


class DeviceOut(BaseModel):
    id: str
    label: str
    created_at: str
    last_seen_at: str | None


class DeviceCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)


class DeviceCreated(DeviceOut):
    token: str = Field(
        description="Shown once and never stored. Lose it and provision another."
    )


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Which machines are reporting about you. On the employee's own screen
    rather than an admin one, because that is a privacy control, not an
    administrative detail."""
    return [
        DeviceOut(
            id=d.id,
            label=d.label,
            created_at=d.created_at.isoformat(),
            last_seen_at=d.last_seen_at.isoformat() if d.last_seen_at else None,
        )
        for d in device_service.list_for_employee(db, user.id)
    ]


@router.post("/devices", response_model=DeviceCreated, status_code=201)
def create_device(
    payload: DeviceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if device_service.active_count(db, user.id) >= device_service.MAX_DEVICES_PER_EMPLOYEE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"You already have {device_service.MAX_DEVICES_PER_EMPLOYEE} registered devices. "
                "Revoke one you no longer use."
            ),
        )

    device, token = device_service.provision(db, user.id, payload.label)
    return DeviceCreated(
        id=device.id,
        label=device.label,
        created_at=device.created_at.isoformat(),
        last_seen_at=None,
        token=token,
    )


@router.delete("/devices/{device_id}", status_code=204)
def revoke_device(
    device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not device_service.revoke(db, device_id, user.id):
        raise HTTPException(status_code=404, detail="Device not found")


@router.get("/status")
def live_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Poll this, not the dashboard. `version` changes only when something
    the employee would notice has changed, so the client can hold its
    render until it actually needs to refetch."""
    return analysis_service.live_status(db, user.id)


# A connector config holds URLs and client ids, not documents. Bounding it
# keeps an authenticated caller from using encrypted storage as a dumping
# ground.
MAX_CONFIG_FIELDS = 12
MAX_CONFIG_VALUE_CHARS = 2000


class ConnectorConfigIn(BaseModel):
    config: dict[str, str] = Field(
        description="The connector's required_config fields. Stored encrypted, never returned.",
        max_length=MAX_CONFIG_FIELDS,
    )

    @field_validator("config")
    @classmethod
    def _bound_values(cls, value: dict[str, str]) -> dict[str, str]:
        for field, item in value.items():
            if len(item) > MAX_CONFIG_VALUE_CHARS:
                raise ValueError(f"'{field}' is longer than {MAX_CONFIG_VALUE_CHARS} characters")
        return value


@router.get("/connectors")
def list_connectors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every connector the build knows about, with this person's state for
    each. Never the stored credential - only a redacted hint, so they can
    tell which URL is saved without it being readable from the API."""
    return {"connectors": connector_service.describe(db, user.id)}


@router.put("/connectors/{connector_key}")
def configure_connector(
    connector_key: str,
    payload: ConnectorConfigIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from integrations import get_connector

    connector = get_connector(connector_key)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_key}'")
    if not connector.metadata.implemented:
        raise HTTPException(
            status_code=400,
            detail=f"{connector.metadata.label} is declared but not implemented yet.",
        )

    missing = [f for f in connector.metadata.required_config if not payload.config.get(f)]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Missing required configuration: {', '.join(missing)}"
        )

    connector_service.save_config(db, user.id, connector_key, payload.config)

    # Sync immediately: a connection that shows "connected" but has pulled
    # nothing is indistinguishable from one that is quietly broken.
    result = connector_service.sync_one(db, user.id, connector_key)
    return {"connector": connector_key, "first_sync": result}


@router.post("/connectors/{connector_key}/sync")
def sync_connector_now(
    connector_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return connector_service.sync_one(db, user.id, connector_key)


@router.delete("/connectors/{connector_key}", status_code=204)
def disconnect_connector(
    connector_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Removes the stored credential outright rather than flagging it
    disabled: an employee disconnecting a calendar means the URL should
    stop existing here."""
    if not connector_service.remove_config(db, user.id, connector_key):
        raise HTTPException(status_code=404, detail="Nothing connected for that source")


class PreferencesOut(BaseModel):
    notifications_enabled: bool


class PreferencesUpdate(BaseModel):
    notifications_enabled: bool


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user)):
    return PreferencesOut(notifications_enabled=user.notifications_enabled)


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Opting out of email is not opting out of support: suggestions still
    appear on the dashboard. Withdrawing *consent* is a different control,
    in the Privacy Center, and deliberately not merged with this one."""
    user.notifications_enabled = payload.notifications_enabled
    db.commit()
    return PreferencesOut(notifications_enabled=user.notifications_enabled)


@router.get("/interventions", response_model=list[InterventionOut])
def list_interventions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        InterventionOut(
            id=row.id,
            type=row.type,
            message=row.message,
            status=row.status,
            employee_response=row.employee_response,
            created_at=row.created_at.isoformat(),
        )
        for row in agent_repo.visible_interventions(db, user.id)
    ]


@router.post("/interventions/{intervention_id}/respond", response_model=InterventionOut)
def respond(
    intervention_id: str,
    payload: InterventionResponseIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    valid = {s.value for s in InterventionStatus}
    if payload.status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(valid)}")

    if agent_repo.get_intervention_for_employee(db, intervention_id, user.id) is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    row = agent_repo.respond_to_intervention(db, intervention_id, payload.status, payload.response)
    return InterventionOut(
        id=row.id,
        type=row.type,
        message=row.message,
        status=row.status,
        employee_response=row.employee_response,
        created_at=row.created_at.isoformat(),
    )


@router.post("/interventions/{intervention_id}/feedback")
def submit_feedback(
    intervention_id: str,
    payload: FeedbackIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if agent_repo.get_intervention_for_employee(db, intervention_id, user.id) is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    row = agent_repo.add_feedback(db, intervention_id, user.id, payload.rating, payload.comment)
    return {"id": row.id, "rating": row.rating, "comment": row.comment}


@router.get("/history")
def daily_history(
    days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Daily feature history for the caller, oldest first - what the
    dashboard sparklines are drawn from, so the trend line is the real
    series rather than decoration."""
    rows = telemetry_repo.daily_features_history(db, user.id, limit_days=min(days, 120))
    return {
        "employee_id": user.id,
        "days": [
            {
                "date": row.date.isoformat(),
                "work_duration": row.work_duration,
                "after_hours": row.after_hours,
                "meeting_hours": row.meeting_hours,
                "focus_minutes": row.focus_minutes,
                "average_break_gap": row.average_break_gap,
                "context_switches": row.context_switches,
            }
            for row in rows
        ],
    }


@router.get("/self-report")
def get_today_self_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SelfReport).filter_by(employee_id=user.id, date=date.today()).first()
    if not row:
        return {"submitted": False}
    return {
        "submitted": True,
        "stress": row.stress,
        "energy": row.energy,
        "recovery": row.recovery,
        "note": row.note,
    }


@router.post("/self-report")
def submit_self_report(
    payload: SelfReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The employee's own check-in. This is the closest thing the system has
    to ground truth - the behavioral signals are only ever a proxy - so it is
    also what the evaluation harness scores against."""
    day = date.fromisoformat(payload.date) if payload.date else date.today()

    existing = db.query(SelfReport).filter_by(employee_id=user.id, date=day).first()
    if existing:
        existing.stress, existing.energy = payload.stress, payload.energy
        existing.recovery, existing.note = payload.recovery, payload.note
    else:
        db.add(
            SelfReport(
                employee_id=user.id,
                date=day,
                stress=payload.stress,
                energy=payload.energy,
                recovery=payload.recovery,
                note=payload.note,
            )
        )
    db.commit()

    daily = telemetry_service.recompute_daily_feature(db, user.id, day)
    return {"date": day.isoformat(), "daily_feature_id": daily.id}
