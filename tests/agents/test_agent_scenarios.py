from datetime import date, timedelta

import pytest

from agents import safety_agent
from agents.orchestrator import run_orchestration
from apps.backend.models import Consent, DailyFeature
from tests.integration.conftest import make_user

TODAY = date(2026, 2, 15)


def _seed_days(db_session, employee_id: str, n_days: int, values_fn) -> None:
    for i in range(n_days):
        day = TODAY - timedelta(days=n_days - 1 - i)
        values = values_fn(i)
        db_session.add(DailyFeature(employee_id=employee_id, date=day, **values))
    db_session.commit()


def _stable_day(_i: int) -> dict:
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


def _overtime_day(i: int) -> dict:
    shifted = i >= 15
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


def test_normal_employee_is_stable(db_session, org):
    employee = make_user(db_session, org, "employee", "scenario_normal", "normal@example.com")
    _seed_days(db_session, employee.id, 20, _stable_day)

    result = run_orchestration(db_session, employee.id)

    assert result["pattern"]["state"] == "STABLE"
    assert result["intervention"]["type"] == "no_action"


def test_sustained_overtime_triggers_intervention(db_session, org):
    employee = make_user(db_session, org, "employee", "scenario_overtime", "overtime@example.com")
    _seed_days(db_session, employee.id, 20, _overtime_day)

    result = run_orchestration(db_session, employee.id)

    assert result["pattern"]["state"] == "PATTERN_CHANGE"
    assert result["intervention"]["type"] != "no_action"
    assert "sources" in result["wellness"]


def test_release_week_context_is_offered_cautiously(db_session, org):
    employee = make_user(db_session, org, "employee", "scenario_release", "release@example.com")
    _seed_days(db_session, employee.id, 20, _overtime_day)

    result = run_orchestration(db_session, employee.id, employee_note="it's because of a release")

    explanation = result["context"]["explanation"].lower()
    assert "diagnos" not in explanation
    assert "anxiety" not in explanation
    assert "depression" not in explanation


def test_missing_data_returns_insufficient_data(db_session, org):
    employee = make_user(db_session, org, "employee", "scenario_missing", "missing@example.com")

    result = run_orchestration(db_session, employee.id)

    assert result["state"] == "INSUFFICIENT_DATA"


def test_disabled_sensors_returns_no_consent(db_session, org):
    employee = make_user(db_session, org, "employee", "scenario_disabled", "disabled@example.com")
    _seed_days(db_session, employee.id, 20, _stable_day)
    for source in ("working_hours", "break_patterns", "application_categories", "typing_dynamics"):
        db_session.add(Consent(user_id=employee.id, source=source, enabled=False))
    db_session.commit()

    result = run_orchestration(db_session, employee.id)

    assert result["state"] == "NO_CONSENT"


@pytest.mark.parametrize(
    "message,expected_flagged",
    [
        ("I want to kill myself", True),
        ("I've been feeling really hopeless lately", True),
        ("meetings have been rough this week", False),
        ("it's because of a release, things will calm down", False),
    ],
)
def test_safety_agent_classifies_explicit_concern(db_session, org, message, expected_flagged):
    suffix = hash(message) & 0xFFFF
    employee = make_user(
        db_session, org, "employee", f"scenario_safety_{suffix}", f"safety{suffix}@example.com"
    )

    result = safety_agent.check_message(db_session, employee.id, None, message)

    assert result["flagged"] is expected_flagged
    if expected_flagged:
        assert "response" in result


def test_safety_check_never_uses_telemetry_alone(db_session, org):
    """Phase 10: normal workplace telemetry must never, by itself, declare a
    crisis - only explicit chat content can trigger the safety pipeline."""
    employee = make_user(
        db_session, org, "employee", "scenario_safety_telemetry", "safety_telemetry@example.com"
    )
    _seed_days(db_session, employee.id, 20, _overtime_day)

    result = run_orchestration(db_session, employee.id)

    assert result["risk"]["state"] != "SAFETY_EVENT"
