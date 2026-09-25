"""Shared seeding helpers.

The day shapes are step changes rather than smooth ramps on purpose: MAD
resists gradual drift by design, so a ramp is a poor way to assert that
detection works. See ml/anomaly/zscore.py.
"""

from datetime import date, timedelta

from apps.backend.models import DailyFeature

TODAY = date(2026, 2, 15)
SHIFT_BREAKPOINT = 15


def seed_days(db_session, employee_id: str, n_days: int, values_fn, end: date = TODAY) -> None:
    for i in range(n_days):
        day = end - timedelta(days=n_days - 1 - i)
        db_session.add(DailyFeature(employee_id=employee_id, date=day, **values_fn(i)))
    db_session.commit()


def stable_day(_i: int) -> dict:
    return {
        "work_duration": 8.0,
        "after_hours": 0.3,
        "break_count": 4,
        "average_break_gap": 100.0,
        "meeting_hours": 1.5,
        "context_switches": 30,
        "focus_minutes": 200.0,
        "typing_speed": 50.0,
        "typing_pause_rate": 0.15,
        "derived": {
            "meeting_load": 0.19,
            "recovery_gap": 0.0,
            "context_switch_rate": 3.75,
            "focus_fragmentation": 0.4,
            "typing_deviation": 0.0,
        },
    }


def overtime_day(i: int) -> dict:
    shifted = i >= SHIFT_BREAKPOINT
    return {
        "work_duration": 11.0 if shifted else 8.0,
        "after_hours": 3.2 if shifted else 0.3,
        "break_count": 2 if shifted else 4,
        "average_break_gap": 220.0 if shifted else 100.0,
        "meeting_hours": 1.5,
        "context_switches": 30,
        "focus_minutes": 150.0 if shifted else 200.0,
        "typing_speed": 44.0 if shifted else 50.0,
        "typing_pause_rate": 0.15,
        "derived": {
            "meeting_load": 0.19,
            "recovery_gap": 2.2 if shifted else 0.0,
            "context_switch_rate": 3.75,
            "focus_fragmentation": 0.4,
            "typing_deviation": 0.0,
        },
    }
