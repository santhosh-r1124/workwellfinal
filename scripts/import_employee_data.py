"""Imports the employee work-pattern dataset into the existing schema.

Usage: python scripts/import_employee_data.py [path/to/employees.csv]

Each CSV row is one employee-day. It is replayed through the same path a
desktop agent's telemetry takes (telemetry_service.ingest_event ->
recompute_daily_feature), so every number on the dashboards is computed by
ml/ exactly as it would be for collected data. Self-reported stress, energy
and recovery become check-ins. Afterwards baselines and the agent workflow
run for every employee, so dashboards are populated without waiting for the
daily sweep.

Dates are moved forward by whole weeks so the most recent row is recent
(weekday rhythm preserved). Safe to re-run: telemetry for imported
employees is replaced, not duplicated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import csv  # noqa: E402
import secrets  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402

from sqlalchemy import delete  # noqa: E402

from apps.backend.core.database import SessionLocal  # noqa: E402
from apps.backend.core.security import hash_password  # noqa: E402
from apps.backend.models import (  # noqa: E402
    Consent,
    DailyFeature,
    Organization,
    Role,
    SelfReport,
    TelemetryEvent,
    User,
)
from apps.backend.services import baseline_service, telemetry_service  # noqa: E402
from shared.enums.data_sources import DataSourceKey  # noqa: E402
from shared.enums.roles import RoleName  # noqa: E402

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "database" / "seeds" / "data" / "employees.csv"

ORG_NAME = "WorkWell AI"
TEAM = "Graduate Trainees"

# Shared portal accounts. In DEMO_MODE the HR / manager and wellness portals
# sign in as these; with DEMO_MODE off they are ordinary accounts that need a
# password set by an admin (scripts/reset_password.py).
PORTAL_ACCOUNTS = [
    ("portal_people", "People & HR Team", "people@workwell.ai", RoleName.MANAGER.value, TEAM),
    ("portal_wellness", "Wellness Team", "wellness@workwell.ai", RoleName.MANAGER.value, TEAM),
    ("portal_admin", "Platform Admin", "admin@workwell.ai", RoleName.ADMIN.value, None),
]

CONSENTED_SOURCES = (
    DataSourceKey.WORKING_HOURS,
    DataSourceKey.BREAK_PATTERNS,
    DataSourceKey.APPLICATION_CATEGORIES,
    DataSourceKey.CALENDAR_METADATA,
)


def _f(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key) or default)
    except ValueError:
        return default


def _scale_1_5(value_1_10: float) -> int:
    return int(max(1, min(5, round(value_1_10 / 2))))


def _get_or_create_role(db, name: str) -> Role:
    role = db.query(Role).filter_by(name=name).first()
    if not role:
        role = Role(name=name, description=f"{name} role")
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def _get_or_create_org(db) -> Organization:
    org = db.query(Organization).filter_by(name=ORG_NAME).first()
    if not org:
        org = Organization(name=ORG_NAME)
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def _upsert_user(db, user_id, full_name, email, org_id, role_id, team) -> User:
    user = db.get(User, user_id) or db.query(User).filter(User.email.ilike(email)).first()
    if user:
        user.full_name, user.org_id, user.role_id, user.team = full_name, org_id, role_id, team
        user.is_active = True
    else:
        user = User(
            id=user_id,
            org_id=org_id,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(secrets.token_urlsafe(24)),
            role_id=role_id,
            team=team,
            timezone="UTC",
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _day_events(day: date, row: dict) -> list[dict]:
    """Spread one CSV day across work sessions separated by breaks, the shape
    the desktop agent reports. Kept within the calendar day so a night shift
    is analysed as that person's own (consistently late) rhythm."""
    work_min = _f(row, "work_duration_hours") * 60
    breaks = int(_f(row, "break_count"))
    break_total = _f(row, "break_duration_minutes")
    sessions = breaks + 1
    meeting_min = _f(row, "meeting_hours") * 60
    focus_min = _f(row, "focus_time_minutes")
    switches = _f(row, "context_switches")

    login = datetime.combine(day, datetime.strptime(row.get("login_time") or "09:00", "%H:%M").time())
    day_end = datetime.combine(day, datetime.max.time()).replace(second=0, microsecond=0)
    span = min(work_min + break_total, (day_end - login).total_seconds() / 60 - 5)
    step = max(span / sessions, 1.0)

    events = []
    for i in range(sessions):
        ts = login + timedelta(minutes=step * i)
        active = work_min / sessions
        events.append(
            {
                "timestamp": ts,
                "active_minutes": round(active, 1),
                "idle_minutes": round(active * 0.05, 1),
                "continuous_session_minutes": round(min(focus_min / sessions, active), 1),
                "context_switches": max(1, int(round(switches / sessions))),
                "application_switch_count": max(1, int(round(switches * 1.3 / sessions))),
                "meeting_minutes": round(meeting_min / sessions, 1),
            }
        )
        if i < breaks:
            events.append(
                {
                    "timestamp": ts + timedelta(minutes=max(step - 1, 0.5)),
                    "break_minutes": round(break_total / max(breaks, 1), 1),
                    "active_minutes": 0.0,
                }
            )
    return events


def import_csv(path: Path, analyse: bool = True) -> None:
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("email") or "").strip()]
    if not rows:
        raise SystemExit("no rows to import")

    latest = max(date.fromisoformat(r["date"]) for r in rows)
    yesterday = date.today() - timedelta(days=1)
    shift = timedelta(days=max(0, (yesterday - latest).days // 7) * 7)

    db = SessionLocal()
    try:
        roles = {r.value: _get_or_create_role(db, r.value) for r in RoleName}
        org = _get_or_create_org(db)

        employees: dict[str, User] = {}
        for row in rows:
            email = row["email"].strip()
            if email.lower() in employees:
                continue
            trainee = (row.get("trainee_id") or "").strip().lower() or secrets.token_hex(4)
            employees[email.lower()] = _upsert_user(
                db, f"emp_{trainee}", row.get("full_name", "").strip() or email,
                email, org.id, roles["employee"].id, TEAM,
            )

        for user_id, name, email, role, team in PORTAL_ACCOUNTS:
            _upsert_user(db, user_id, name, email, org.id, roles[role].id, team)

        ids = [u.id for u in employees.values()]
        for model in (TelemetryEvent, DailyFeature, SelfReport):
            db.execute(delete(model).where(model.employee_id.in_(ids)))
        db.commit()

        for user in employees.values():
            for source in CONSENTED_SOURCES:
                consent = db.query(Consent).filter_by(user_id=user.id, source=source.value).first()
                if consent:
                    consent.enabled = True
                else:
                    db.add(Consent(user_id=user.id, source=source.value, enabled=True))
        db.commit()

        rows.sort(key=lambda r: (r["email"].lower(), r["date"]))
        for row in rows:
            user = employees[row["email"].strip().lower()]
            day = date.fromisoformat(row["date"]) + shift
            for event in _day_events(day, row):
                ts = event.pop("timestamp")
                telemetry_service.ingest_event(db, user.id, ts, event)
            db.add(
                SelfReport(
                    employee_id=user.id,
                    date=day,
                    stress=_scale_1_5(_f(row, "stress_level", 5)),
                    energy=_scale_1_5(_f(row, "energy_level", 5)),
                    recovery=_scale_1_5(_f(row, "work_life_balance_score", 6)),
                )
            )
            db.commit()
            telemetry_service.recompute_daily_feature(db, user.id, day)

        for user in employees.values():
            result = baseline_service.recompute_baselines(db, user.id) or {}
            print(f"{user.full_name}: {result.get('state', 'baseline building')}")

        if analyse:
            from agents.orchestrator import run_orchestration

            for user in employees.values():
                try:
                    run_orchestration(db, user.id)
                except Exception as exc:  # analysis is refreshed by the worker anyway
                    db.rollback()
                    print(f"analysis deferred for {user.full_name}: {exc}")

        print(f"Imported {len(rows)} employee-days for {len(employees)} employees.")
    finally:
        db.close()


if __name__ == "__main__":
    import_csv(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV)
