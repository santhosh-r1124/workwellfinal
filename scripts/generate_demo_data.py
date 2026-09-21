"""Generates ~30 days of synthetic telemetry + self-reports for five demo
employees, each exhibiting a distinct work-pattern archetype (Phase 2.4),
then recomputes baselines and patterns so the dashboard has something
meaningful to show immediately after `docker compose up`.

Usage: python scripts/generate_demo_data.py

Requires database/seeds/seed_demo.py to have been run first (creates the
demo users this script writes telemetry for).
"""
import random
from datetime import date, datetime, time, timedelta

from apps.backend.core.database import SessionLocal
from apps.backend.models import Consent, SelfReport
from apps.backend.services import baseline_service, telemetry_service
from shared.enums.data_sources import DataSourceKey

random.seed(42)

TOTAL_DAYS = 30
START_DATE = date.today() - timedelta(days=TOTAL_DAYS)

PATTERNS = {
    "employee_a": "normal",
    "employee_b": "increasing_overtime",
    "employee_c": "meeting_overload",
    "employee_d": "fragmented",
    "employee_e": "stable_high",
}


def _noise(scale: float) -> float:
    return random.uniform(-scale, scale)


def _lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


SHIFT_BREAKPOINT = TOTAL_DAYS - 10


def _step(day_index: int, before: float, after: float, noise: float) -> float:
    """A stable baseline period followed by a sustained shift, rather than a
    slow ramp - a robust median/MAD detector is deliberately insensitive to
    smooth secular drift (that's a feature, not a bug: it avoids
    over-alerting on gradual, self-adapting trends), so demo archetypes
    meant to demonstrate detection use a clear step instead."""
    base = before if day_index < SHIFT_BREAKPOINT else after
    return base + _noise(noise)


def _daily_params(pattern: str, day_index: int) -> dict:
    t = day_index / (TOTAL_DAYS - 1)

    if pattern == "normal":
        return {
            "work_duration": 8.0 + _noise(0.3),
            "after_hours": max(0.0, 0.3 + _noise(0.15)),
            "break_count": round(_clip(4 + _noise(0.6), 1, 6)),
            "meeting_hours": max(0.0, 1.5 + _noise(0.3)),
            "context_switches": max(5, 30 + _noise(5)),
            "typing_speed": 50 + _noise(2),
            "typing_pause_rate": max(0.05, 0.15 + _noise(0.02)),
            "focus_minutes": 8.0 * 60 * 0.55 + _noise(10),
        }
    if pattern == "increasing_overtime":
        work_duration = _lerp(8.0, 11.2, t) + _noise(0.2)
        return {
            "work_duration": work_duration,
            "after_hours": max(0.0, _lerp(0.3, 3.2, t) + _noise(0.15)),
            "break_count": round(_clip(_lerp(4, 2, t) + _noise(0.4), 1, 6)),
            "meeting_hours": max(0.0, 1.8 + _noise(0.3)),
            "context_switches": max(5, 32 + _noise(5)),
            "typing_speed": _lerp(50, 44, t) + _noise(2),
            "typing_pause_rate": max(0.05, _lerp(0.15, 0.28, t) + _noise(0.02)),
            "focus_minutes": work_duration * 60 * _lerp(0.55, 0.4, t) + _noise(10),
        }
    if pattern == "meeting_overload":
        work_duration = 9.0 + _noise(0.2)
        meeting_hours = max(0.0, _step(day_index, 2.0, 5.6, 0.2))
        return {
            "work_duration": work_duration,
            "after_hours": max(0.0, 0.4 + _noise(0.15)),
            "break_count": round(_clip(_step(day_index, 4, 3, 0.4), 1, 6)),
            "meeting_hours": meeting_hours,
            "context_switches": max(5, _step(day_index, 30, 55, 5)),
            "typing_speed": 49 + _noise(2),
            "typing_pause_rate": max(0.05, 0.16 + _noise(0.02)),
            "focus_minutes": max(15.0, work_duration * 60 - meeting_hours * 60 * 0.9 + _noise(10)),
        }
    if pattern == "fragmented":
        work_duration = 8.5 + _noise(0.2)
        return {
            "work_duration": work_duration,
            "after_hours": max(0.0, 0.3 + _noise(0.15)),
            "break_count": round(_clip(4 + _noise(0.5), 1, 6)),
            "meeting_hours": max(0.0, 1.6 + _noise(0.2)),
            "context_switches": max(5, _step(day_index, 25, 95, 5)),
            "typing_speed": 48 + _noise(2),
            "typing_pause_rate": max(0.05, 0.17 + _noise(0.02)),
            "focus_minutes": max(15.0, _step(day_index, 180, 45, 10)),
        }
    if pattern == "stable_high":
        work_duration = 10.4 + _noise(0.15)
        return {
            "work_duration": work_duration,
            "after_hours": max(0.0, 0.6 + _noise(0.1)),
            "break_count": round(_clip(3 + _noise(0.3), 1, 6)),
            "meeting_hours": max(0.0, 2.2 + _noise(0.2)),
            "context_switches": max(5, 35 + _noise(4)),
            "typing_speed": 52 + _noise(1.5),
            "typing_pause_rate": max(0.05, 0.14 + _noise(0.015)),
            "focus_minutes": work_duration * 60 * 0.5 + _noise(10),
        }
    raise ValueError(f"Unknown pattern: {pattern}")


def _self_report(pattern: str, day_index: int) -> dict:
    t = day_index / (TOTAL_DAYS - 1)
    if pattern in ("increasing_overtime", "meeting_overload"):
        stress = _clip(round(_lerp(2, 4.5, t) + _noise(0.4)), 1, 5)
        energy = _clip(round(_lerp(4, 2, t) + _noise(0.4)), 1, 5)
        recovery = _clip(round(_lerp(4, 2, t) + _noise(0.4)), 1, 5)
    elif pattern == "fragmented":
        stress = _clip(round(_lerp(2.5, 3.5, t) + _noise(0.4)), 1, 5)
        energy = _clip(round(_lerp(3.5, 2.8, t) + _noise(0.4)), 1, 5)
        recovery = _clip(round(3 + _noise(0.4)), 1, 5)
    else:
        stress = _clip(round(2.3 + _noise(0.4)), 1, 5)
        energy = _clip(round(3.7 + _noise(0.4)), 1, 5)
        recovery = _clip(round(3.6 + _noise(0.4)), 1, 5)
    return {"stress": int(stress), "energy": int(energy), "recovery": int(recovery)}


def _build_day_events(day: date, params: dict) -> list[dict]:
    events = []
    after_hours_min = params["after_hours"] * 60
    daytime_active = max(0.0, params["work_duration"] * 60 - after_hours_min)
    break_count = int(params["break_count"])
    n_sessions = max(break_count, 1) + 1

    session_active = daytime_active / n_sessions
    session_switches = params["context_switches"] / n_sessions
    session_continuous = params["focus_minutes"] / n_sessions
    session_meeting = params["meeting_hours"] * 60 / n_sessions

    cursor = datetime.combine(day, time(9, 0))
    for i in range(n_sessions):
        events.append(
            {
                "timestamp": cursor,
                "active_minutes": round(session_active, 1),
                "idle_minutes": round(session_active * 0.05, 1),
                "continuous_session_minutes": round(min(session_continuous, session_active), 1),
                "application_switch_count": max(1, int(session_switches * 1.3)),
                "context_switches": max(1, int(session_switches)),
                "typing_speed": round(params["typing_speed"] + _noise(2), 1),
                "pause_rate": round(max(0.0, params["typing_pause_rate"] + _noise(0.02)), 3),
                "backspace_rate": round(max(0.0, 0.05 + _noise(0.01)), 3),
                "correction_rate": round(max(0.0, 0.04 + _noise(0.01)), 3),
                "typing_burst_length": round(8 + _noise(1), 1),
                "inter_key_interval": round(0.18 + _noise(0.01), 3),
                "meeting_minutes": round(session_meeting, 1),
            }
        )
        cursor += timedelta(minutes=90)
        if i < break_count:
            events.append({"timestamp": cursor, "break_minutes": 15.0, "active_minutes": 0.0})
            cursor += timedelta(minutes=15)

    if after_hours_min > 0:
        events.append(
            {
                "timestamp": datetime.combine(day, time(19, 30)),
                "active_minutes": round(after_hours_min, 1),
                "idle_minutes": round(after_hours_min * 0.05, 1),
                "continuous_session_minutes": round(after_hours_min * 0.6, 1),
                "context_switches": max(1, int(params["context_switches"] * 0.1)),
                "application_switch_count": max(1, int(params["context_switches"] * 0.13)),
                "typing_speed": round(params["typing_speed"] * 0.9, 1),
                "pause_rate": round(max(0.0, params["typing_pause_rate"] * 1.2), 3),
            }
        )
    return events


def _enable_demo_consents(db, employee_id: str) -> None:
    for source in (
        DataSourceKey.WORKING_HOURS,
        DataSourceKey.BREAK_PATTERNS,
        DataSourceKey.APPLICATION_CATEGORIES,
        DataSourceKey.TYPING_DYNAMICS,
        DataSourceKey.CALENDAR_METADATA,
    ):
        existing = db.query(Consent).filter_by(user_id=employee_id, source=source.value).first()
        if not existing:
            db.add(Consent(user_id=employee_id, source=source.value, enabled=True))
    db.commit()


def generate() -> None:
    db = SessionLocal()
    try:
        for employee_id, pattern in PATTERNS.items():
            _enable_demo_consents(db, employee_id)

            for day_index in range(TOTAL_DAYS):
                day = START_DATE + timedelta(days=day_index)
                if day.weekday() >= 5 and pattern != "increasing_overtime":
                    continue

                params = _daily_params(pattern, day_index)
                for event in _build_day_events(day, params):
                    timestamp = event.pop("timestamp")
                    telemetry_service.ingest_event(db, employee_id, timestamp, event)

                if random.random() < 0.7:
                    report = _self_report(pattern, day_index)
                    existing = db.query(SelfReport).filter_by(employee_id=employee_id, date=day).first()
                    if not existing:
                        db.add(SelfReport(employee_id=employee_id, date=day, **report))
                        db.commit()

                telemetry_service.recompute_daily_feature(db, employee_id, day)

            pattern_result = baseline_service.recompute_baselines(db, employee_id)
            print(f"{employee_id} ({pattern}): pattern state = {pattern_result.get('state', 'n/a')}")

        print("Synthetic demo data generated for:", ", ".join(PATTERNS))
    finally:
        db.close()


if __name__ == "__main__":
    generate()
