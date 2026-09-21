from datetime import datetime, timezone

from sqlalchemy import select

from apps.backend.models import Consent, TelemetryEvent
from apps.backend.services import telemetry_service
from tests.integration.conftest import auth_headers, make_user


def test_disabled_typing_dynamics_never_persisted(db_session, org):
    employee = make_user(db_session, org, "employee", "priv_emp1", "priv1@example.com")
    db_session.add(Consent(user_id=employee.id, source="typing_dynamics", enabled=False))
    db_session.commit()

    telemetry_service.ingest_event(
        db_session,
        employee.id,
        datetime.now(timezone.utc),
        {"active_minutes": 30, "typing_speed": 55.0, "pause_rate": 0.2},
    )

    stored = db_session.scalar(
        select(TelemetryEvent).where(TelemetryEvent.employee_id == employee.id)
    )
    assert "typing_speed" not in stored.features
    assert "pause_rate" not in stored.features
    assert stored.features["active_minutes"] == 30


def test_disabled_working_hours_strips_active_minutes(db_session, org):
    employee = make_user(db_session, org, "employee", "priv_emp2", "priv2@example.com")
    db_session.add(Consent(user_id=employee.id, source="working_hours", enabled=False))
    db_session.commit()

    telemetry_service.ingest_event(
        db_session,
        employee.id,
        datetime.now(timezone.utc),
        {"active_minutes": 30, "idle_minutes": 5, "typing_speed": 55.0},
    )

    stored = db_session.scalar(
        select(TelemetryEvent).where(TelemetryEvent.employee_id == employee.id)
    )
    assert "active_minutes" not in stored.features
    assert "idle_minutes" not in stored.features
    assert stored.features["typing_speed"] == 55.0


def test_manager_cannot_access_employee_wellness_data(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "priv_emp3", "priv3@example.com")
    make_user(db_session, org, "manager", "priv_mgr1", "priv_mgr1@example.com")

    headers = auth_headers(app_client, "priv_mgr1@example.com")
    res = app_client.get(f"/employees/{employee.id}/baseline", headers=headers)
    assert res.status_code == 403


def test_employee_can_access_their_own_baseline(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "priv_emp4", "priv4@example.com")
    headers = auth_headers(app_client, "priv4@example.com")

    res = app_client.get(f"/employees/{employee.id}/baseline", headers=headers)
    assert res.status_code == 200


def test_admin_can_access_employee_wellness_data(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "priv_emp5", "priv5@example.com")
    make_user(db_session, org, "admin", "priv_admin1", "priv_admin1@example.com")

    headers = auth_headers(app_client, "priv_admin1@example.com")
    res = app_client.get(f"/employees/{employee.id}/baseline", headers=headers)
    assert res.status_code == 200


def test_gemini_api_key_never_exposed_to_frontend(app_client):
    configured_secret = "test-key"  # matches conftest's GEMINI_API_KEY
    for path in ("/health", "/openapi.json"):
        response = app_client.get(path)
        assert configured_secret not in response.text
