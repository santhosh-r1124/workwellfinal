from datetime import date

from apps.backend.models import Consent
from apps.backend.services import integration_service
from tests.integration.conftest import auth_headers, make_user
from tests.unit.test_integrations import SAMPLE_ICS


def _write_ics(tmp_path):
    ics_file = tmp_path / "calendar.ics"
    ics_file.write_text(SAMPLE_ICS)
    return str(ics_file)


def test_sync_ingests_meeting_minutes_when_consented(db_session, org, tmp_path):
    employee = make_user(db_session, org, "employee", "sync_ok", "sync_ok@example.com")
    # calendar_metadata is off by default, so it has to be opted into.
    db_session.add(Consent(user_id=employee.id, source="calendar_metadata", enabled=True))
    db_session.commit()

    result = integration_service.sync_connector(
        db_session,
        "ics_calendar",
        {"ics_path_or_url": _write_ics(tmp_path)},
        employee.id,
        date(2026, 2, 10),
        date(2026, 2, 11),
    )

    assert result["ingested_days"] == 2
    assert result["skipped_reason"] is None

    from apps.backend.repositories import telemetry_repo

    daily = telemetry_repo.daily_features_history(db_session, employee.id)
    meeting_hours = {row.date.isoformat(): row.meeting_hours for row in daily}
    assert meeting_hours["2026-02-10"] == 1.25
    assert meeting_hours["2026-02-11"] == 1.0


def test_sync_is_skipped_without_consent(db_session, org, tmp_path):
    """calendar_metadata defaults to off - the connector must not run at
    all, not merely have its output filtered."""
    employee = make_user(db_session, org, "employee", "sync_noconsent", "sync_noconsent@example.com")

    result = integration_service.sync_connector(
        db_session,
        "ics_calendar",
        {"ics_path_or_url": _write_ics(tmp_path)},
        employee.id,
        date(2026, 2, 10),
        date(2026, 2, 11),
    )

    assert result["ingested_days"] == 0
    assert "calendar_metadata" in result["skipped_reason"]

    from apps.backend.repositories import telemetry_repo

    assert telemetry_repo.daily_features_history(db_session, employee.id) == []


def test_admin_can_list_connectors(app_client, db_session, org):
    make_user(db_session, org, "admin", "int_admin", "int_admin@example.com")
    headers = auth_headers(app_client, "int_admin@example.com")

    res = app_client.get("/admin/integrations", headers=headers)
    assert res.status_code == 200

    by_key = {c["key"]: c for c in res.json()["connectors"]}
    assert by_key["ics_calendar"]["implemented"] is True
    assert by_key["microsoft_graph"]["implemented"] is False


def test_non_admin_cannot_list_connectors(app_client, db_session, org):
    make_user(db_session, org, "employee", "int_emp", "int_emp@example.com")
    headers = auth_headers(app_client, "int_emp@example.com")

    assert app_client.get("/admin/integrations", headers=headers).status_code == 403
