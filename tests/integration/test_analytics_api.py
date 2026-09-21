from datetime import date, timedelta

from apps.backend.models import DailyFeature
from tests.integration.conftest import auth_headers, make_user


def _seed_team(db_session, org, team: str, size: int, prefix: str) -> list[str]:
    ids = []
    for i in range(size):
        user = make_user(db_session, org, "employee", f"{prefix}{i}", f"{prefix}{i}@example.com")
        user.team = team
        ids.append(user.id)
    db_session.commit()

    today = date.today()
    for employee_id in ids:
        for day_offset in range(1, 28):
            day = today - timedelta(days=day_offset)
            recent = day_offset <= 14
            db_session.add(
                DailyFeature(
                    employee_id=employee_id,
                    date=day,
                    work_duration=9.0 if recent else 8.0,
                    after_hours=1.5 if recent else 0.5,
                    meeting_hours=4.0 if recent else 2.0,
                    average_break_gap=150.0 if recent else 100.0,
                    focus_minutes=120.0 if recent else 200.0,
                    context_switches=60 if recent else 30,
                    break_count=3,
                    typing_speed=50.0,
                    typing_pause_rate=0.15,
                    derived={},
                )
            )
    db_session.commit()
    return ids


def test_manager_sees_team_aggregate_not_individuals(app_client, db_session, org):
    employee_ids = _seed_team(db_session, org, "Engineering", 6, "eng_ok_")
    manager = make_user(db_session, org, "manager", "mgr_ok", "mgr_ok@example.com")
    manager.team = "Engineering"
    db_session.commit()

    headers = auth_headers(app_client, "mgr_ok@example.com")
    res = app_client.get("/analytics/teams/Engineering", headers=headers)
    assert res.status_code == 200

    body = res.json()
    assert body["sufficient_cohort"] is True
    assert body["metrics"]["meeting_hours"]["change_pct"] == 100.0
    assert body["metrics"]["focus_minutes"]["direction"] == "down"

    # The privacy guarantee: no employee identifier anywhere in the payload.
    for employee_id in employee_ids:
        assert employee_id not in res.text


def test_small_team_is_suppressed(app_client, db_session, org):
    _seed_team(db_session, org, "Tiny", 3, "tiny_")
    make_user(db_session, org, "manager", "mgr_tiny", "mgr_tiny@example.com")

    headers = auth_headers(app_client, "mgr_tiny@example.com")
    res = app_client.get("/analytics/teams/Tiny", headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert body["sufficient_cohort"] is False
    assert body["metrics"] == {}


def test_employee_cannot_access_team_analytics(app_client, db_session, org):
    make_user(db_session, org, "employee", "emp_analytics", "emp_analytics@example.com")
    headers = auth_headers(app_client, "emp_analytics@example.com")

    res = app_client.get("/analytics/teams/Engineering", headers=headers)
    assert res.status_code == 403


def test_manager_still_cannot_read_an_individual_baseline(app_client, db_session, org):
    """The two halves of the rule together: aggregates yes, individuals no."""
    employee = make_user(db_session, org, "employee", "eng_indiv", "eng_indiv@example.com")
    make_user(db_session, org, "manager", "mgr_indiv", "mgr_indiv@example.com")

    headers = auth_headers(app_client, "mgr_indiv@example.com")
    assert app_client.get(f"/employees/{employee.id}/baseline", headers=headers).status_code == 403
