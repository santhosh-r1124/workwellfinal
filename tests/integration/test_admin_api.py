from datetime import date, datetime, timedelta, timezone

from apps.backend.models import DailyFeature, TelemetryEvent
from ml.aggregation.cohort import ABSOLUTE_MIN_COHORT
from tests.integration.conftest import auth_headers, make_user


def test_admin_can_read_and_update_settings(app_client, db_session, org):
    make_user(db_session, org, "admin", "admin_settings", "admin_settings@example.com")
    headers = auth_headers(app_client, "admin_settings@example.com")

    res = app_client.get("/admin/settings", headers=headers)
    assert res.status_code == 200
    assert res.json()["retention_days"] == 90

    res2 = app_client.patch("/admin/settings", json={"retention_days": 30}, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["retention_days"] == 30


def test_admin_cannot_lower_cohort_threshold_below_floor(app_client, db_session, org):
    make_user(db_session, org, "admin", "admin_cohort", "admin_cohort@example.com")
    headers = auth_headers(app_client, "admin_cohort@example.com")

    res = app_client.patch("/admin/settings", json={"aggregation_min_cohort": 2}, headers=headers)
    assert res.status_code == 200
    assert res.json()["aggregation_min_cohort"] == ABSOLUTE_MIN_COHORT


def test_non_admin_cannot_reach_admin_endpoints(app_client, db_session, org):
    make_user(db_session, org, "manager", "mgr_admin_probe", "mgr_admin_probe@example.com")
    headers = auth_headers(app_client, "mgr_admin_probe@example.com")

    for path in ("/admin/settings", "/admin/audit-logs", "/admin/data-sources"):
        assert app_client.get(path, headers=headers).status_code == 403


def test_data_source_catalog_marks_never_collectible(app_client, db_session, org):
    make_user(db_session, org, "admin", "admin_sources", "admin_sources@example.com")
    headers = auth_headers(app_client, "admin_sources@example.com")

    res = app_client.get("/admin/data-sources", headers=headers)
    sources = {s["key"]: s for s in res.json()["data_sources"]}

    assert sources["raw_keyboard"]["never_collectible"] is True
    assert sources["webcam"]["never_collectible"] is True
    assert sources["working_hours"]["never_collectible"] is False


def test_retention_deletes_only_data_past_the_window(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "admin_retention", "admin_retention@example.com")
    employee = make_user(db_session, org, "employee", "emp_retention", "emp_retention@example.com")

    old_day = date.today() - timedelta(days=200)
    recent_day = date.today() - timedelta(days=2)
    for day in (old_day, recent_day):
        db_session.add(
            DailyFeature(employee_id=employee.id, date=day, work_duration=8.0, derived={})
        )
        db_session.add(
            TelemetryEvent(
                employee_id=employee.id,
                timestamp=datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc),
                features={"active_minutes": 60},
            )
        )
    db_session.commit()

    headers = auth_headers(app_client, admin.email)
    res = app_client.post("/admin/retention/apply", headers=headers)
    assert res.status_code == 200
    assert res.json()["daily_features_deleted"] == 1
    assert res.json()["telemetry_events_deleted"] == 1

    remaining = db_session.query(DailyFeature).filter_by(employee_id=employee.id).all()
    assert [r.date for r in remaining] == [recent_day]


def test_audit_log_records_admin_actions(app_client, db_session, org):
    make_user(db_session, org, "admin", "admin_audit", "admin_audit@example.com")
    headers = auth_headers(app_client, "admin_audit@example.com")

    app_client.patch("/admin/settings", json={"retention_days": 45}, headers=headers)
    res = app_client.get("/admin/audit-logs", headers=headers)

    actions = [entry["action"] for entry in res.json()["logs"]]
    assert "admin.settings_update" in actions
