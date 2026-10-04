from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import AgentRun, Feedback, Intervention
from shared.constants.wellbeing import INTERVENTION_VISIBLE_DAYS


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


def intervention_within_cooldown(
    db: Session, employee_id: str, type_: str, cooldown_days: int
) -> Intervention | None:
    """The scheduler runs daily, but a sustained pattern is by definition
    the same finding on consecutive days. Without this, an employee whose
    pattern persists for three weeks gets twenty-one identical nudges -
    which is how a wellbeing product turns into something people mute.

    A nudge is suppressed while an earlier one of the same type is either
    inside the cooldown window or still unanswered, whichever is longer:
    silence is not consent to ask again.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
    stmt = (
        select(Intervention)
        .where(
            Intervention.employee_id == employee_id,
            Intervention.type == type_,
            (Intervention.created_at >= cutoff) | (Intervention.status == "proposed"),
        )
        .order_by(Intervention.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def latest_agent_run(db: Session, employee_id: str) -> AgentRun | None:
    stmt = (
        select(AgentRun)
        .where(AgentRun.employee_id == employee_id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def visible_interventions(db: Session, employee_id: str) -> list[Intervention]:
    """What the employee should see on their dashboard right now.

    Not the same question as "what has ever been proposed". Two rules:

    * one per type, newest first - a sustained pattern produces the same
      finding repeatedly, and the newest is the one that reflects current
      evidence. Without this the dashboard stacks up near-identical cards.
    * nothing older than the visible window - a nudge nobody answered two
      weeks ago has stopped being a suggestion.

    Dismissed ones stay until they age out rather than vanishing on click,
    so the employee can still rate a suggestion they just turned down;
    that rating is the only signal the feedback loop gets about a bad one.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=INTERVENTION_VISIBLE_DAYS)
    stmt = (
        select(Intervention)
        .where(Intervention.employee_id == employee_id, Intervention.created_at >= cutoff)
        .order_by(Intervention.created_at.desc())
    )

    seen: set[str] = set()
    visible = []
    for row in db.scalars(stmt):
        if row.type in seen:
            continue
        seen.add(row.type)
        visible.append(row)
    return visible


def get_intervention_for_employee(
    db: Session, intervention_id: str, employee_id: str
) -> Intervention | None:
    """Scoped lookup: an intervention id alone must never be enough to read
    or act on another employee's nudge."""
    row = db.get(Intervention, intervention_id)
    if row is None or row.employee_id != employee_id:
        return None
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


def interventions_with_feedback(db: Session, intervention_ids: list[str]) -> set[str]:
    """Which of these interventions the employee has already rated.

    The follow-up prompt ("did this help?") hangs off this: a suggestion that
    has been rated has closed the loop and should not keep asking. Done as one
    query over the visible set rather than per-card, so a dashboard with a
    handful of nudges is still a single round trip.
    """
    if not intervention_ids:
        return set()
    stmt = select(Feedback.intervention_id).where(Feedback.intervention_id.in_(intervention_ids))
    return set(db.scalars(stmt))


def recent_agent_runs(db: Session, employee_id: str, limit: int = 10) -> list[AgentRun]:
    stmt = (
        select(AgentRun)
        .where(AgentRun.employee_id == employee_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
