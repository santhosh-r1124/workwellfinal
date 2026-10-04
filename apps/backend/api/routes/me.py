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
from apps.backend.core import timezones
from apps.backend.core.security import hash_password, verify_password
from apps.backend.models import SelfReport, User
from apps.backend.repositories import agent_repo, telemetry_repo
from apps.backend.services import (
    analysis_service,
    audit_service,
    connector_service,
    device_service,
    support_service,
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
    # Whether the employee has already rated this one. Drives the "did this
    # help?" follow-up: a rated suggestion has closed the loop and stops
    # asking. Defaults true so a single-row response (respond()) never
    # re-prompts before the list has told the client otherwise.
    has_feedback: bool = True


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


class PasswordChange(BaseModel):
    current_password: str
    # Long rather than complex: length is what actually resists guessing,
    # and character-class rules mostly produce Password1!.
    new_password: str = Field(min_length=12, max_length=200)


@router.post("/password", status_code=204)
def change_password(
    payload: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Without this, an account created by an admin is stuck on a password
    that admin has seen - which is most accounts, since that is how people
    get added."""
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="That is the current password")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()

    audit_service.record(
        db,
        actor_id=user.id,
        subject_user_id=user.id,
        action="auth.password_changed",
        resource=f"user:{user.id}",
        meta={},
    )


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
    timezone: str


class PreferencesUpdate(BaseModel):
    notifications_enabled: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user)):
    return PreferencesOut(
        notifications_enabled=user.notifications_enabled, timezone=user.timezone
    )


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Opting out of email is not opting out of support: suggestions still
    appear on the dashboard. Withdrawing *consent* is a different control,
    in the Privacy Center, and deliberately not merged with this one.

    Timezone decides where this employee's day ends, and the whole
    analysis is built on days. The browser reports it, so nobody has to
    pick their own out of six hundred.
    """
    if payload.notifications_enabled is not None:
        user.notifications_enabled = payload.notifications_enabled

    if payload.timezone is not None:
        if not timezones.is_valid(payload.timezone):
            raise HTTPException(status_code=400, detail="Unknown timezone")
        user.timezone = payload.timezone

    db.commit()
    return PreferencesOut(
        notifications_enabled=user.notifications_enabled, timezone=user.timezone
    )


@router.get("/interventions", response_model=list[InterventionOut])
def list_interventions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = agent_repo.visible_interventions(db, user.id)
    rated = agent_repo.interventions_with_feedback(db, [r.id for r in rows])
    return [
        InterventionOut(
            id=row.id,
            type=row.type,
            message=row.message,
            status=row.status,
            employee_response=row.employee_response,
            created_at=row.created_at.isoformat(),
            has_feedback=row.id in rated,
        )
        for row in rows
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


@router.get("/self-report/history")
def self_report_history(
    days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The employee's own check-in series, oldest first - what the wellbeing
    pulse trend is drawn from. Stress/energy/recovery are the person's own
    1-5 ratings, never a model's inference, so this is the one line on the
    dashboard that is ground truth rather than proxy.

    Only the caller's own reports, and only the numbers: the free-text note
    is deliberately left out of the series so a trend that may be glanced at
    over someone's shoulder carries no words.
    """
    window = min(max(days, 1), 120)
    rows = (
        db.query(SelfReport)
        .filter_by(employee_id=user.id)
        .order_by(SelfReport.date.desc())
        .limit(window)
        .all()
    )
    rows.reverse()
    return {
        "employee_id": user.id,
        "reports": [
            {
                "date": row.date.isoformat(),
                "stress": row.stress,
                "energy": row.energy,
                "recovery": row.recovery,
            }
            for row in rows
        ],
    }


@router.get("/support-resources")
def my_support_resources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Where this employee can turn for help, as published by their org. The
    employee view hides retired resources; an admin sees all of them through
    /admin/support-resources."""
    return {"resources": support_service.list_for_org(db, user.org_id, active_only=True)}
