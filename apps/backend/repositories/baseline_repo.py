from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import EmployeeBaseline, PatternStateRecord


def upsert_baseline(db: Session, employee_id: str, metric: str, values: dict) -> EmployeeBaseline:
    existing = db.scalar(
        select(EmployeeBaseline).where(
            EmployeeBaseline.employee_id == employee_id, EmployeeBaseline.metric == metric
        )
    )
    if existing:
        for k, v in values.items():
            setattr(existing, k, v)
        row = existing
    else:
        row = EmployeeBaseline(employee_id=employee_id, metric=metric, **values)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_baselines(db: Session, employee_id: str) -> list[EmployeeBaseline]:
    return list(
        db.scalars(select(EmployeeBaseline).where(EmployeeBaseline.employee_id == employee_id))
    )


def recent_pattern_states(db: Session, employee_id: str, limit: int = 30) -> list[PatternStateRecord]:
    stmt = (
        select(PatternStateRecord)
        .where(PatternStateRecord.employee_id == employee_id)
        .order_by(PatternStateRecord.date.desc())
        .limit(limit)
    )
    return list(reversed(list(db.scalars(stmt))))


def save_pattern_state(db: Session, employee_id: str, date_, state: str, confidence: float,
                        duration_days: int, signals: list[dict]) -> PatternStateRecord:
    row = PatternStateRecord(
        employee_id=employee_id,
        date=date_,
        state=state,
        confidence=confidence,
        duration_days=duration_days,
        signals=signals,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
