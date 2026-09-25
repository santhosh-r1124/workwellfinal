from apps.backend.models import AgentRun, Intervention
from tests.integration.conftest import auth_headers, make_user


def _make_intervention(db_session, employee_id: str) -> Intervention:
    run = AgentRun(employee_id=employee_id, context={}, risk={}, intervention={}, wellness={})
    db_session.add(run)
    db_session.commit()

    row = Intervention(
        employee_id=employee_id,
        agent_run_id=run.id,
        type="focus_block",
        message="You might consider protecting one focus block tomorrow.",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_employee_sees_own_interventions(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "me_emp1", "me1@example.com")
    _make_intervention(db_session, employee.id)

    headers = auth_headers(app_client, "me1@example.com")
    res = app_client.get("/me/interventions", headers=headers)

    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["type"] == "focus_block"
    assert res.json()[0]["status"] == "proposed"


def test_responding_updates_status(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "me_emp2", "me2@example.com")
    intervention = _make_intervention(db_session, employee.id)

    headers = auth_headers(app_client, "me2@example.com")
    res = app_client.post(
        f"/me/interventions/{intervention.id}/respond",
        json={"status": "accepted"},
        headers=headers,
    )

    assert res.status_code == 200
    assert res.json()["status"] == "accepted"


def test_invalid_status_is_rejected(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "me_emp3", "me3@example.com")
    intervention = _make_intervention(db_session, employee.id)

    headers = auth_headers(app_client, "me3@example.com")
    res = app_client.post(
        f"/me/interventions/{intervention.id}/respond",
        json={"status": "obliterated"},
        headers=headers,
    )
    assert res.status_code == 400


def test_cannot_act_on_another_employees_intervention(app_client, db_session, org):
    """An intervention id alone must not be enough to act on someone else's
    nudge."""
    owner = make_user(db_session, org, "employee", "me_owner", "me_owner@example.com")
    make_user(db_session, org, "employee", "me_other", "me_other@example.com")
    intervention = _make_intervention(db_session, owner.id)

    headers = auth_headers(app_client, "me_other@example.com")

    assert (
        app_client.post(
            f"/me/interventions/{intervention.id}/respond",
            json={"status": "accepted"},
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        app_client.post(
            f"/me/interventions/{intervention.id}/feedback",
            json={"rating": 5},
            headers=headers,
        ).status_code
        == 404
    )


def test_feedback_is_stored(app_client, db_session, org):
    from apps.backend.models import Feedback

    employee = make_user(db_session, org, "employee", "me_emp4", "me4@example.com")
    intervention = _make_intervention(db_session, employee.id)

    headers = auth_headers(app_client, "me4@example.com")
    res = app_client.post(
        f"/me/interventions/{intervention.id}/feedback",
        json={"rating": 4, "comment": "useful"},
        headers=headers,
    )

    assert res.status_code == 200
    stored = db_session.query(Feedback).filter_by(intervention_id=intervention.id).one()
    assert stored.rating == 4


def test_self_report_round_trip(app_client, db_session, org):
    make_user(db_session, org, "employee", "me_emp5", "me5@example.com")
    headers = auth_headers(app_client, "me5@example.com")

    assert app_client.get("/me/self-report", headers=headers).json()["submitted"] is False

    post = app_client.post(
        "/me/self-report", json={"stress": 4, "energy": 2, "recovery": 2}, headers=headers
    )
    assert post.status_code == 200

    fetched = app_client.get("/me/self-report", headers=headers).json()
    assert fetched["submitted"] is True
    assert fetched["stress"] == 4


def test_self_report_resubmission_updates_rather_than_duplicates(app_client, db_session, org):
    from apps.backend.models import SelfReport

    employee = make_user(db_session, org, "employee", "me_emp6", "me6@example.com")
    headers = auth_headers(app_client, "me6@example.com")

    app_client.post("/me/self-report", json={"stress": 2, "energy": 4, "recovery": 4}, headers=headers)
    app_client.post("/me/self-report", json={"stress": 5, "energy": 1, "recovery": 1}, headers=headers)

    rows = db_session.query(SelfReport).filter_by(employee_id=employee.id).all()
    assert len(rows) == 1
    assert rows[0].stress == 5


def test_self_report_validates_scale(app_client, db_session, org):
    make_user(db_session, org, "employee", "me_emp7", "me7@example.com")
    headers = auth_headers(app_client, "me7@example.com")

    res = app_client.post(
        "/me/self-report", json={"stress": 9, "energy": 2, "recovery": 2}, headers=headers
    )
    assert res.status_code == 422


def test_me_routes_require_auth(app_client):
    assert app_client.get("/me/interventions").status_code == 401
    assert app_client.get("/me/self-report").status_code == 401


def test_the_dashboard_shows_one_suggestion_per_type(app_client, db_session, org):
    """A sustained pattern produces the same finding repeatedly. Without
    this the dashboard stacks up near-identical cards and the employee has
    to work out which one is current."""
    from datetime import datetime, timedelta, timezone

    from apps.backend.models import AgentRun, Intervention

    employee = make_user(db_session, org, "employee", "vis_emp", "vis_emp@example.com")
    run = AgentRun(employee_id=employee.id, context={}, risk={}, intervention={}, wellness={})
    db_session.add(run)
    db_session.commit()

    now = datetime.now(timezone.utc)
    for days_ago, type_, message in [
        (0, "recovery_break", "newest recovery"),
        (4, "recovery_break", "older recovery"),
        (8, "recovery_break", "oldest recovery"),
        (1, "focus_block", "focus"),
    ]:
        db_session.add(
            Intervention(
                employee_id=employee.id,
                agent_run_id=run.id,
                type=type_,
                message=message,
                created_at=now - timedelta(days=days_ago),
            )
        )
    db_session.commit()

    rows = app_client.get("/me/interventions", headers=auth_headers(app_client, employee.email)).json()

    assert [r["type"] for r in rows] == ["recovery_break", "focus_block"]
    assert rows[0]["message"] == "newest recovery"


def test_a_suggestion_nobody_answered_a_fortnight_ago_stops_being_shown(
    app_client, db_session, org
):
    from datetime import datetime, timedelta, timezone

    from apps.backend.models import AgentRun, Intervention

    employee = make_user(db_session, org, "employee", "stale_emp", "stale_emp@example.com")
    run = AgentRun(employee_id=employee.id, context={}, risk={}, intervention={}, wellness={})
    db_session.add(run)
    db_session.commit()
    db_session.add(
        Intervention(
            employee_id=employee.id,
            agent_run_id=run.id,
            type="recovery_break",
            message="from a month ago",
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
    )
    db_session.commit()

    rows = app_client.get("/me/interventions", headers=auth_headers(app_client, employee.email)).json()

    assert rows == []


def test_the_live_status_token_changes_only_when_something_changed(app_client, db_session, org):
    """The client polls this instead of the dashboard's real payload, so a
    token that churns on its own would defeat the point."""
    employee = make_user(db_session, org, "employee", "live_emp", "live_emp@example.com")
    headers = auth_headers(app_client, employee.email)

    first = app_client.get("/me/status", headers=headers).json()
    second = app_client.get("/me/status", headers=headers).json()

    assert first["version"] == second["version"]

    _make_intervention(db_session, employee.id)

    third = app_client.get("/me/status", headers=headers).json()
    assert third["version"] != first["version"]
    assert third["open_interventions"] == 1


def test_live_status_is_scoped_to_the_caller(app_client, db_session, org):
    mine = make_user(db_session, org, "employee", "live_mine", "live_mine@example.com")
    theirs = make_user(db_session, org, "employee", "live_theirs", "live_theirs@example.com")
    _make_intervention(db_session, theirs.id)

    status = app_client.get("/me/status", headers=auth_headers(app_client, mine.email)).json()

    assert status["open_interventions"] == 0
