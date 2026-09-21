from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import DailyFeature, SelfReport, TelemetryEvent


def create_event(db: Session, employee_id: str, timestamp: datetime, features: dict) -> TelemetryEvent:
    event = TelemetryEvent(employee_id=employee_id, timestamp=timestamp, features=features)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def events_for_day(db: Session, employee_id: str, day: date) -> list[TelemetryEvent]:
    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)
    stmt = (
        select(TelemetryEvent)
        .where(
            TelemetryEvent.employee_id == employee_id,
            TelemetryEvent.timestamp >= start,
            TelemetryEvent.timestamp <= end,
        )
        .order_by(TelemetryEvent.timestamp)
    )
    return list(db.scalars(stmt))


def self_report_for_day(db: Session, employee_id: str, day: date) -> SelfReport | None:
    return db.scalar(
        select(SelfReport).where(SelfReport.employee_id == employee_id, SelfReport.date == day)
    )


def upsert_daily_feature(db: Session, employee_id: str, day: date, values: dict) -> DailyFeature:
    existing = db.scalar(
        select(DailyFeature).where(DailyFeature.employee_id == employee_id, DailyFeature.date == day)
    )
    if existing:
        for k, v in values.items():
            setattr(existing, k, v)
        row = existing
    else:
        row = DailyFeature(employee_id=employee_id, date=day, **values)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def daily_features_history(db: Session, employee_id: str, limit_days: int = 60) -> list[DailyFeature]:
    stmt = (
        select(DailyFeature)
        .where(DailyFeature.employee_id == employee_id)
        .order_by(DailyFeature.date.desc())
        .limit(limit_days)
    )
    return list(reversed(list(db.scalars(stmt))))


def daily_feature_to_dict(row: DailyFeature) -> dict:
    return {
        "date": row.date,
        "work_duration": row.work_duration,
        "after_hours": row.after_hours,
        "break_count": row.break_count,
        "average_break_gap": row.average_break_gap,
        "meeting_hours": row.meeting_hours,
        "context_switches": row.context_switches,
        "focus_minutes": row.focus_minutes,
        "typing_speed": row.typing_speed,
        "typing_pause_rate": row.typing_pause_rate,
        "self_report_stress": row.self_report_stress,
        "self_report_energy": row.self_report_energy,
        "self_report_recovery": row.self_report_recovery,
        **(row.derived or {}),
    }
