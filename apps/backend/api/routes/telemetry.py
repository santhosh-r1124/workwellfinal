from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.backend.api.deps import authenticated_device, get_db
from apps.backend.core.config import get_settings
from apps.backend.models import SelfReport
from apps.backend.services import analysis_service, baseline_service, telemetry_service
from shared.schemas.telemetry import SelfReportIn, TelemetryEventIn

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def _assert_own_device(device, employee_id: str) -> None:
    """The device's binding, not the request body, decides whose data may
    be written. The body still carries an employee_id so a mismatch is a
    loud 403 rather than data silently landing somewhere unexpected."""
    if employee_id != device.employee_id:
        raise HTTPException(
            status_code=403,
            detail="This device is not registered to that employee",
        )


@router.post("/events")
def post_event(
    payload: TelemetryEventIn,
    db: Session = Depends(get_db),
    device=Depends(authenticated_device),
):
    _assert_own_device(device, payload.employee_id)

    event = telemetry_service.ingest_event(
        db, payload.employee_id, payload.timestamp, payload.features.model_dump(exclude_none=True)
    )
    daily = telemetry_service.recompute_daily_feature(db, payload.employee_id, payload.timestamp.date())

    # Features are recomputed inline - that is cheap and has to be
    # immediate. The analysis is not, so it goes to the worker, where the
    # hourly dedupe key means an agent reporting every five minutes still
    # costs one run per hour.
    if get_settings().reanalyse_on_ingest:
        analysis_service.request_refresh(db, payload.employee_id)

    return {"event_id": event.id, "daily_feature_id": daily.id}


@router.post("/self-report")
def post_self_report(
    payload: SelfReportIn,
    db: Session = Depends(get_db),
    device=Depends(authenticated_device),
):
    _assert_own_device(device, payload.employee_id)

    day_value = date_cls.fromisoformat(payload.date)

    existing = db.query(SelfReport).filter_by(employee_id=payload.employee_id, date=day_value).first()
    if existing:
        existing.stress, existing.energy, existing.recovery, existing.note = (
            payload.stress,
            payload.energy,
            payload.recovery,
            payload.note,
        )
    else:
        db.add(
            SelfReport(
                employee_id=payload.employee_id,
                date=day_value,
                stress=payload.stress,
                energy=payload.energy,
                recovery=payload.recovery,
                note=payload.note,
            )
        )
    db.commit()

    daily = telemetry_service.recompute_daily_feature(db, payload.employee_id, day_value)
    return {"daily_feature_id": daily.id}


@router.post("/{employee_id}/recompute-baseline")
def recompute_baseline(
    employee_id: str,
    db: Session = Depends(get_db),
    device=Depends(authenticated_device),
):
    _assert_own_device(device, employee_id)
    pattern = baseline_service.recompute_baselines(db, employee_id)
    return {"pattern": pattern}
