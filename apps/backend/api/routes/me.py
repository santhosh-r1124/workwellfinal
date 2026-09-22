"""Employee self-service endpoints.

Every route here acts on the authenticated caller. There is deliberately no
employee_id in any path or body: it removes a whole class of IDOR mistakes,
and it matches the product rule that this data belongs to the person it is
about.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.models import SelfReport, User
from apps.backend.repositories import agent_repo
from apps.backend.services import telemetry_service
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
        for row in agent_repo.recent_interventions(db, user.id)
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
