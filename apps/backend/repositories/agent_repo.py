from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import AgentRun, Feedback, Intervention


def create_agent_run(
    db: Session,
    employee_id: str,
    pattern_state_id: str | None,
    context: dict,
    risk: dict,
    intervention: dict,
    wellness: dict,
) -> AgentRun:
    row = AgentRun(
        employee_id=employee_id,
        pattern_state_id=pattern_state_id,
        context=context,
        risk=risk,
        intervention=intervention,
        wellness=wellness,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_intervention(
    db: Session, employee_id: str, agent_run_id: str, type_: str, message: str
) -> Intervention:
    row = Intervention(employee_id=employee_id, agent_run_id=agent_run_id, type=type_, message=message)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def respond_to_intervention(db: Session, intervention_id: str, status: str, response: str | None) -> Intervention | None:
    from datetime import datetime, timezone

    row = db.get(Intervention, intervention_id)
    if not row:
        return None
    row.status = status
    row.employee_response = response
    row.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def add_feedback(db: Session, intervention_id: str, employee_id: str, rating: int | None, comment: str | None) -> Feedback:
    row = Feedback(intervention_id=intervention_id, employee_id=employee_id, rating=rating, comment=comment)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def recent_agent_runs(db: Session, employee_id: str, limit: int = 10) -> list[AgentRun]:
    stmt = (
        select(AgentRun)
        .where(AgentRun.employee_id == employee_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
