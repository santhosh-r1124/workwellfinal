"""Connecting a calendar, from the employee's own screen.

The connector framework and a working ICS client already existed and
nothing could drive them. These cover the path that was missing, and the
two properties that make it safe to expose: the stored URL is a bearer
credential, and consent still decides what is collected.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from apps.backend.models import ConnectorConfig, Consent, DailyFeature, TelemetryEvent
from apps.backend.services import connector_service
from tests.integration.conftest import auth_headers, make_user

TODAY = date.today()


def write_ics(tmp_path, days_ago_to_minutes: dict[int, int]) -> str:
    lines = ["BEGIN:VCALENDAR"]
    for days_ago, minutes in days_ago_to_minutes.items():
        day = TODAY - timedelta(days=days_ago)
        stamp = day.strftime("%Y%m%d")
        end_hour = 9 + minutes // 60
        end_min = minutes % 60
        lines += [
            "BEGIN:VEVENT",
            "SUMMARY:Something private that must never be stored",
            f"DTSTART:{stamp}T090000Z",
            f"DTEND:{stamp}T{end_hour:02d}{end_min:02d}00Z",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")

    path = tmp_path / "calendar.ics"
    path.write_text("\n".join(lines))
    return str(path)


@pytest.fixture()
def employee(db_session, org):
    user = make_user(db_session, org, "employee", "conn_emp", "conn_emp@example.com")
    # calendar_metadata is off by default; these tests are about the
    # connector, so turn it on except where consent is the subject.
    db_session.add(Consent(user_id=user.id, source="calendar_metadata", enabled=True))
    db_session.commit()
    return user


def test_connecting_a_calendar_pulls_meeting_time_in(app_client, db_session, employee, tmp_path):
    headers = auth_headers(app_client, employee.email)
    ics = write_ics(tmp_path, {1: 90, 2: 30})

    res = app_client.put(
        "/me/connectors/ics_calendar",
        json={"config": {"ics_path_or_url": ics}},
        headers=headers,
    )

    assert res.status_code == 200, res.text
    assert res.json()["first_sync"]["status"] == "ok"
    assert res.json()["first_sync"]["ingested_days"] == 2

    days = db_session.scalars(
        select(DailyFeature).where(DailyFeature.employee_id == employee.id)
    ).all()
    assert {d.date for d in days} == {TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
    assert sorted(d.meeting_hours for d in days) == [0.5, 1.5]


def test_only_times_cross_the_boundary_never_event_content(
    app_client, db_session, employee, tmp_path
):
    """The calendar says what the meeting was about. That must not be
    anywhere in this database."""
    headers = auth_headers(app_client, employee.email)
    ics = write_ics(tmp_path, {1: 60})

    app_client.put(
        "/me/connectors/ics_calendar",
        json={"config": {"ics_path_or_url": ics}},
        headers=headers,
    )

    events = db_session.scalars(
        select(TelemetryEvent).where(TelemetryEvent.employee_id == employee.id)
    ).all()
    assert events
    for event in events:
        assert "Something private" not in str(event.features)
        assert set(event.features) <= {"meeting_minutes"}


def test_the_stored_url_is_encrypted_and_never_returned(app_client, db_session, employee, tmp_path):
    """A private subscribe URL is a bearer credential: anyone holding it
    reads that calendar, indefinitely, without the owner being told."""
    headers = auth_headers(app_client, employee.email)
    ics = write_ics(tmp_path, {1: 60})

    app_client.put(
        "/me/connectors/ics_calendar",
        json={"config": {"ics_path_or_url": ics}},
        headers=headers,
    )

    row = db_session.scalar(
        select(ConnectorConfig).where(ConnectorConfig.employee_id == employee.id)
    )
    assert ics not in row.encrypted_config
    assert "ics_path_or_url" not in row.encrypted_config

    listed = app_client.get("/me/connectors", headers=headers).json()["connectors"]
    ics_entry = next(c for c in listed if c["key"] == "ics_calendar")
    assert ics_entry["connected"] is True
    assert ics not in str(listed)
    assert "…" in ics_entry["config_hint"]


def test_a_rotated_app_secret_asks_for_a_reconnect_rather_than_crashing(
    db_session, employee, tmp_path, monkeypatch
):
    ics = write_ics(tmp_path, {1: 60})
    connector_service.save_config(db_session, employee.id, "ics_calendar", {"ics_path_or_url": ics})

    from apps.backend.core import crypto

    crypto._fernet.cache_clear()
    monkeypatch.setattr(crypto.get_settings(), "app_secret_key", "a-different-secret-entirely")
    crypto._fernet.cache_clear()

    result = connector_service.sync_one(db_session, employee.id, "ics_calendar")

    crypto._fernet.cache_clear()
    assert result["status"] == "needs_reconnect"


def test_a_connector_collects_nothing_while_its_consent_is_off(
    app_client, db_session, org, tmp_path
):
    """Connecting a source must not be a way around the Privacy Centre."""
    user = make_user(db_session, org, "employee", "conn_noconsent", "conn_noconsent@example.com")
    db_session.add(Consent(user_id=user.id, source="calendar_metadata", enabled=False))
    db_session.commit()

    headers = auth_headers(app_client, user.email)
    ics = write_ics(tmp_path, {1: 60})

    res = app_client.put(
        "/me/connectors/ics_calendar",
        json={"config": {"ics_path_or_url": ics}},
        headers=headers,
    )

    assert res.json()["first_sync"]["status"] == "consent_off"
    assert not db_session.scalars(
        select(DailyFeature).where(DailyFeature.employee_id == user.id)
    ).all()


def test_disconnecting_removes_the_credential_outright(app_client, db_session, employee, tmp_path):
    headers = auth_headers(app_client, employee.email)
    app_client.put(
        "/me/connectors/ics_calendar",
        json={"config": {"ics_path_or_url": write_ics(tmp_path, {1: 60})}},
        headers=headers,
    )

    assert app_client.delete("/me/connectors/ics_calendar", headers=headers).status_code == 204
    assert not db_session.scalars(
        select(ConnectorConfig).where(ConnectorConfig.employee_id == employee.id)
    ).all()


def test_one_employee_cannot_see_or_touch_anothers_connection(
    app_client, db_session, org, employee, tmp_path
):
    connector_service.save_config(
        db_session, employee.id, "ics_calendar", {"ics_path_or_url": write_ics(tmp_path, {1: 60})}
    )
    other = make_user(db_session, org, "employee", "conn_other", "conn_other@example.com")
    headers = auth_headers(app_client, other.email)

    listed = app_client.get("/me/connectors", headers=headers).json()["connectors"]
    assert all(c["connected"] is False for c in listed)

    assert app_client.delete("/me/connectors/ics_calendar", headers=headers).status_code == 404
    assert db_session.scalar(
        select(ConnectorConfig).where(ConnectorConfig.employee_id == employee.id)
    ) is not None


def test_a_declared_but_unimplemented_connector_is_refused_not_stored(
    app_client, db_session, employee
):
    """Storing a Slack client secret against a connector with no client
    would look configured and do nothing."""
    res = app_client.put(
        "/me/connectors/slack",
        json={"config": {"client_id": "x", "client_secret": "y"}},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 400
    assert not db_session.scalars(
        select(ConnectorConfig).where(ConnectorConfig.employee_id == employee.id)
    ).all()


def test_missing_configuration_is_rejected_with_the_field_named(app_client, db_session, employee):
    res = app_client.put(
        "/me/connectors/ics_calendar",
        json={"config": {}},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 400
    assert "ics_path_or_url" in res.json()["detail"]


def test_an_unknown_connector_is_a_404(app_client, db_session, employee):
    res = app_client.put(
        "/me/connectors/not_a_thing",
        json={"config": {"x": "y"}},
        headers=auth_headers(app_client, employee.email),
    )
    assert res.status_code == 404


def test_a_broken_calendar_url_is_reported_not_raised(db_session, employee):
    connector_service.save_config(
        db_session, employee.id, "ics_calendar", {"ics_path_or_url": "/no/such/file.ics"}
    )

    result = connector_service.sync_one(db_session, employee.id, "ics_calendar")

    assert result["status"] == "failed"
    row = connector_service.get_config(db_session, employee.id, "ics_calendar")
    assert row.last_sync_status == "failed"


def test_the_sweep_only_enqueues_employees_who_connected_something(
    db_session, org, employee, tmp_path
):
    make_user(db_session, org, "employee", "conn_none", "conn_none@example.com")
    connector_service.save_config(
        db_session, employee.id, "ics_calendar", {"ics_path_or_url": write_ics(tmp_path, {1: 60})}
    )

    assert connector_service.employees_with_connectors(db_session) == [employee.id]
