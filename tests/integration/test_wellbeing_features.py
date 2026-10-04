"""Phase-later features: wellbeing pulse trend (B), support resources (C),
and the intervention follow-up loop (D). Each test is named as the sentence
it proves.
"""

from apps.backend.models import AgentRun, Intervention
from tests.integration.conftest import auth_headers, make_user

# --- B: wellbeing pulse trend -------------------------------------------------


def test_self_report_history_returns_the_series_oldest_first(app_client, db_session, org):
    make_user(db_session, org, "employee", "pulse_emp", "pulse@example.com")
    headers = auth_headers(app_client, "pulse@example.com")

    app_client.post(
        "/me/self-report",
        json={"stress": 2, "energy": 4, "recovery": 4, "date": "2026-09-01"},
        headers=headers,
    )
    app_client.post(
        "/me/self-report",
        json={"stress": 5, "energy": 1, "recovery": 1, "date": "2026-09-03"},
        headers=headers,
    )

    res = app_client.get("/me/self-report/history", headers=headers)
    assert res.status_code == 200
    reports = res.json()["reports"]
    assert [r["date"] for r in reports] == ["2026-09-01", "2026-09-03"]
    assert reports[0]["stress"] == 2
    assert reports[1]["stress"] == 5


def test_self_report_history_carries_no_free_text_note(app_client, db_session, org):
    """The trend may be glanced at over someone's shoulder, so the series
    carries only the numbers - never the words the employee typed."""
    make_user(db_session, org, "employee", "pulse_note", "pulse_note@example.com")
    headers = auth_headers(app_client, "pulse_note@example.com")

    app_client.post(
        "/me/self-report",
        json={"stress": 3, "energy": 3, "recovery": 3, "note": "rough week after the release"},
        headers=headers,
    )

    reports = app_client.get("/me/self-report/history", headers=headers).json()["reports"]
    assert reports and "note" not in reports[0]


def test_self_report_history_is_scoped_to_the_caller(app_client, db_session, org):
    mine = make_user(db_session, org, "employee", "pulse_mine", "pulse_mine@example.com")
    theirs = make_user(db_session, org, "employee", "pulse_theirs", "pulse_theirs@example.com")

    app_client.post(
        "/me/self-report",
        json={"stress": 5, "energy": 1, "recovery": 1},
        headers=auth_headers(app_client, theirs.email),
    )

    reports = app_client.get(
        "/me/self-report/history", headers=auth_headers(app_client, mine.email)
    ).json()["reports"]
    assert reports == []


# --- C: support resources -----------------------------------------------------


def _add_resource(app_client, admin_email, **body) -> dict:
    payload = {"label": "EAP", "category": "general"}
    payload.update(body)
    res = app_client.post(
        "/admin/support-resources", json=payload, headers=auth_headers(app_client, admin_email)
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_admin_publishes_a_resource_and_employees_can_read_it(app_client, db_session, org):
    make_user(db_session, org, "admin", "sr_admin", "sr_admin@example.com")
    make_user(db_session, org, "employee", "sr_emp", "sr_emp@example.com")

    _add_resource(
        app_client,
        "sr_admin@example.com",
        label="Employee Assistance Line",
        category="counselling",
        phone="0800-000-000",
    )

    seen = app_client.get(
        "/me/support-resources", headers=auth_headers(app_client, "sr_emp@example.com")
    ).json()["resources"]
    assert len(seen) == 1
    assert seen[0]["label"] == "Employee Assistance Line"
    assert seen[0]["phone"] == "0800-000-000"


def test_a_crisis_resource_sorts_first_regardless_of_order(app_client, db_session, org):
    make_user(db_session, org, "admin", "sr_admin2", "sr_admin2@example.com")

    _add_resource(app_client, "sr_admin2@example.com", label="Gym discount", category="benefits", sort_order=0)
    _add_resource(app_client, "sr_admin2@example.com", label="Crisis line", category="crisis", sort_order=9)

    resources = app_client.get(
        "/me/support-resources", headers=auth_headers(app_client, "sr_admin2@example.com")
    ).json()["resources"]
    assert resources[0]["label"] == "Crisis line"


def test_an_unknown_category_is_refused(app_client, db_session, org):
    make_user(db_session, org, "admin", "sr_admin3", "sr_admin3@example.com")
    res = app_client.post(
        "/admin/support-resources",
        json={"label": "x", "category": "severity-4"},
        headers=auth_headers(app_client, "sr_admin3@example.com"),
    )
    assert res.status_code == 400


def test_deleting_a_resource_removes_it_from_the_employee_view(app_client, db_session, org):
    make_user(db_session, org, "admin", "sr_admin4", "sr_admin4@example.com")
    created = _add_resource(app_client, "sr_admin4@example.com", label="Temporary notice")

    headers = auth_headers(app_client, "sr_admin4@example.com")
    assert app_client.delete(f"/admin/support-resources/{created['id']}", headers=headers).status_code == 204
    assert app_client.get("/me/support-resources", headers=headers).json()["resources"] == []


def test_an_admin_cannot_delete_another_orgs_resource(app_client, db_session, org):
    from apps.backend.models import Organization

    make_user(db_session, org, "admin", "sr_owner", "sr_owner@example.com")
    created = _add_resource(app_client, "sr_owner@example.com", label="Ours")

    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    make_user(db_session, other_org, "admin", "sr_intruder", "sr_intruder@example.com")

    res = app_client.delete(
        f"/admin/support-resources/{created['id']}",
        headers=auth_headers(app_client, "sr_intruder@example.com"),
    )
    assert res.status_code == 404


def test_a_non_admin_cannot_publish_a_resource(app_client, db_session, org):
    make_user(db_session, org, "employee", "sr_plain", "sr_plain@example.com")
    res = app_client.post(
        "/admin/support-resources",
        json={"label": "x"},
        headers=auth_headers(app_client, "sr_plain@example.com"),
    )
    assert res.status_code == 403


# --- D: intervention follow-up loop -------------------------------------------


def _make_intervention(db_session, employee_id: str) -> Intervention:
    run = AgentRun(employee_id=employee_id, context={}, risk={}, intervention={}, wellness={})
    db_session.add(run)
    db_session.commit()
    row = Intervention(
        employee_id=employee_id,
        agent_run_id=run.id,
        type="recovery_break",
        message="Consider protecting a recovery break.",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_an_unrated_suggestion_still_asks_did_this_help(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "fb_unrated", "fb_unrated@example.com")
    _make_intervention(db_session, employee.id)

    rows = app_client.get(
        "/me/interventions", headers=auth_headers(app_client, employee.email)
    ).json()
    assert rows[0]["has_feedback"] is False


def test_a_rated_suggestion_closes_the_loop_and_stops_asking(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "fb_rated", "fb_rated@example.com")
    intervention = _make_intervention(db_session, employee.id)
    headers = auth_headers(app_client, employee.email)

    app_client.post(
        f"/me/interventions/{intervention.id}/feedback", json={"rating": 4}, headers=headers
    )

    rows = app_client.get("/me/interventions", headers=headers).json()
    assert rows[0]["has_feedback"] is True
