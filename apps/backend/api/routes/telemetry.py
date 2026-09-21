from datetime import date as date_cls

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_db, verify_agent_token
from apps.backend.models import SelfReport
from apps.backend.services import baseline_service, telemetry_service
from shared.schemas.telemetry import SelfReportIn, TelemetryEventIn

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", dependencies=[Depends(verify_agent_token)])
def post_event(payload: TelemetryEventIn, db: Session = Depends(get_db)):
    event = telemetry_service.ingest_event(
        db, payload.employee_id, payload.timestamp, payload.features.model_dump(exclude_none=True)
    )
    daily = telemetry_service.recompute_daily_feature(db, payload.employee_id, payload.timestamp.date())
    return {"event_id": event.id, "daily_feature_id": daily.id}


@router.post("/self-report", dependencies=[Depends(verify_agent_token)])
def post_self_report(payload: SelfReportIn, db: Session = Depends(get_db)):
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


@router.post("/{employee_id}/recompute-baseline", dependencies=[Depends(verify_agent_token)])
def recompute_baseline(employee_id: str, db: Session = Depends(get_db)):
    pattern = baseline_service.recompute_baselines(db, employee_id)
    return {"pattern": pattern}
