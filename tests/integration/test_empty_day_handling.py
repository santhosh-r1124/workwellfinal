"""A day with no telemetry must not read as a day of zero work.

Found by running the UI: submitting a check-in creates a daily-feature row
for today before any telemetry has arrived, and the dashboard rendered every
signal at 0.0 / -100%.
"""

from datetime import date, timedelta

from apps.backend.models import DailyFeature
from apps.backend.services import baseline_service
from tests.integration.conftest import auth_headers, make_user


def _seed_worked_days(db_session, employee_id: str, days: int = 12) -> None:
    """Seeds worked days down to offset 2, leaving today and yesterday free
    for the empty rows each test adds."""
    today = date.today()
    for offset in range(days, 1, -1):
        db_session.add(
            DailyFeature(
                employee_id=employee_id,
                date=today - timedelta(days=offset),
                work_duration=8.0,
                after_hours=0.4,
                break_count=4,
                average_break_gap=100.0,
                meeting_hours=2.0,
                context_switches=30,
                focus_minutes=200.0,
                typing_speed=50.0,
                typing_pause_rate=0.15,
                derived={},
            )
        )
    db_session.commit()


def test_empty_today_does_not_zero_out_the_dashboard(db_session, org):
    employee = make_user(db_session, org, "employee", "empty_day1", "empty1@example.com")
    _seed_worked_days(db_session, employee.id)

    # What a self-report before any telemetry produces.
    db_session.add(
        DailyFeature(
            employee_id=employee.id,
            date=date.today(),
            work_duration=0.0,
            self_report_stress=4,
            derived={},
        )
    )
    db_session.commit()

    baseline_service.recompute_baselines(db_session, employee.id)
    response = baseline_service.get_baseline_response(db_session, employee.id)

    work = response["metrics"]["work_duration"]
    assert work["current"] == 8.0, "current should fall back to the last measured day"
    assert work["deviation"] == 0.0


def test_empty_days_do_not_drag_the_baseline(db_session, org):
    employee = make_user(db_session, org, "employee", "empty_day2", "empty2@example.com")
    _seed_worked_days(db_session, employee.id)

    for offset in (0, 1):
        db_session.add(
            DailyFeature(
                employee_id=employee.id,
                date=date.today() - timedelta(days=offset),
                work_duration=0.0,
                derived={},
            )
        )
    db_session.commit()

    baseline_service.recompute_baselines(db_session, employee.id)
    response = baseline_service.get_baseline_response(db_session, employee.id)

    # Median of twelve 8.0 days; the zero rows must not pull it down.
    assert response["metrics"]["work_duration"]["baseline"] == 8.0


def test_dashboard_endpoint_reflects_the_fix(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "empty_day3", "empty3@example.com")
    _seed_worked_days(db_session, employee.id)
    baseline_service.recompute_baselines(db_session, employee.id)

    headers = auth_headers(app_client, "empty3@example.com")
    app_client.post(
        "/me/self-report", json={"stress": 4, "energy": 2, "recovery": 2}, headers=headers
    )

    res = app_client.get(f"/employees/{employee.id}/baseline", headers=headers)
    assert res.json()["metrics"]["work_duration"]["current"] == 8.0
