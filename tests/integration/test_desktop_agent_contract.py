"""The desktop agent's payload must be accepted by the telemetry endpoint.

These two halves are written in different languages of the same repo and
never imported by each other, so nothing but a test keeps them in step:
DesktopFeatures forbids unknown fields, which means any field the agent
starts emitting - or renames - fails the request rather than being silently
dropped.

The OS collectors can't run headless, so the raw-input layer is stubbed. What
is exercised is everything after it: the consent gate, feature assembly, and
the wire format.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from apps.backend.models import TelemetryEvent
from apps.backend.services import device_service
from tests.integration.conftest import make_user

DESKTOP_AGENT_ROOT = Path(__file__).resolve().parents[2] / "apps" / "desktop-agent"
if str(DESKTOP_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(DESKTOP_AGENT_ROOT))

from collectors.window_tracker import WindowTracker  # noqa: E402
from main import collect_features  # noqa: E402
from privacy.consent_gate import ConsentGate  # noqa: E402
from processors.session_tracker import SessionTracker  # noqa: E402

ALL_SOURCES = {
    "working_hours": True,
    "break_patterns": True,
    "application_categories": True,
    "typing_dynamics": True,
    "calendar_metadata": True,
}


class StubActivityCollector:
    """Stands in for the pynput-backed collector, same return shape."""

    def drain_window(self):
        return {
            "typing_speed": 52.4,
            "inter_key_interval": 0.18,
            "pause_rate": 0.21,
            "backspace_rate": 0.05,
            "correction_rate": 0.05,
            "typing_burst_length": 8.2,
        }


def build_agent_features(consent: dict) -> dict:
    gate = ConsentGate(consent)

    session = SessionTracker()
    for _ in range(40):
        session.record_tick(idle_seconds=0, tick_seconds=30)
    for _ in range(12):
        session.record_tick(idle_seconds=999, tick_seconds=30)

    tracker = WindowTracker(poll_interval_seconds=30)
    tracker._switch_count = 23
    tracker._meeting_seconds = 1800

    return collect_features(gate, session, tracker, StubActivityCollector())


def device_headers(db_session, employee) -> dict:
    """A real provisioned device token, bound to this employee."""
    _, token = device_service.provision(db_session, employee.id, "test laptop")
    return {"Authorization": f"Bearer {token}"}


def test_agent_payload_is_accepted_by_the_endpoint(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "agent_ok", "agent_ok@example.com")
    agent_headers = device_headers(db_session, employee)
    features = build_agent_features(dict(ALL_SOURCES))

    res = app_client.post(
        "/telemetry/events",
        json={
            "employee_id": employee.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features": features,
        },
        headers=agent_headers,
    )

    assert res.status_code == 200, res.text

    stored = db_session.scalar(
        select(TelemetryEvent).where(TelemetryEvent.employee_id == employee.id)
    )
    assert stored.source == "desktop_agent"
    assert stored.features["active_minutes"] == 20.0


def test_every_field_the_agent_emits_is_a_known_feature(app_client, db_session, org):
    """DesktopFeatures forbids extras, so this fails loudly if the agent
    adds a field the schema doesn't know about."""
    employee = make_user(db_session, org, "employee", "agent_fields", "agent_fields@example.com")
    agent_headers = device_headers(db_session, employee)
    features = build_agent_features(dict(ALL_SOURCES))

    res = app_client.post(
        "/telemetry/events",
        json={
            "employee_id": employee.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features": features,
        },
        headers=agent_headers,
    )
    assert res.status_code == 200, f"agent emitted a field the API rejects: {res.text}"


def test_device_side_consent_gate_drops_fields_before_upload():
    """Defence in depth: the device shouldn't even compute a disabled
    signal, independently of the server-side strip."""
    gated = build_agent_features(
        {**ALL_SOURCES, "typing_dynamics": False, "calendar_metadata": False}
    )

    for field in ("typing_speed", "pause_rate", "correction_rate", "meeting_minutes"):
        assert field not in gated

    assert gated["active_minutes"] == 20.0
    assert gated["context_switches"] == 23


def test_working_hours_off_still_reports_breaks():
    """The two consent sources share one idle-tracking loop but gate
    different fields, so they have to come apart cleanly."""
    gated = build_agent_features({**ALL_SOURCES, "working_hours": False})

    assert "active_minutes" not in gated
    assert "idle_minutes" not in gated
    assert "break_minutes" in gated


def test_agent_sends_nothing_when_all_consent_is_off():
    assert build_agent_features(dict.fromkeys(ALL_SOURCES, False)) == {}


def test_endpoint_rejects_a_bad_agent_token(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "agent_auth", "agent_auth@example.com")

    res = app_client.post(
        "/telemetry/events",
        json={
            "employee_id": employee.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features": {"active_minutes": 30},
        },
        headers={"Authorization": "Bearer not-the-agent-token"},
    )
    assert res.status_code == 401


def test_a_device_cannot_report_for_someone_else(app_client, db_session, org):
    """The whole reason per-device tokens replaced a shared secret: with
    one shared credential, anyone who could read an agent config - a file
    on their own laptop - could post fabricated telemetry as a colleague."""
    mine = make_user(db_session, org, "employee", "agent_mine", "agent_mine@example.com")
    colleague = make_user(db_session, org, "employee", "agent_theirs", "agent_theirs@example.com")

    res = app_client.post(
        "/telemetry/events",
        json={
            "employee_id": colleague.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features": {"active_minutes": 600},
        },
        headers=device_headers(db_session, mine),
    )

    assert res.status_code == 403
    assert not db_session.scalars(
        select(TelemetryEvent).where(TelemetryEvent.employee_id == colleague.id)
    ).all()


def test_a_revoked_device_stops_being_accepted(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "agent_revoked", "agent_revoked@example.com")
    device, token = device_service.provision(db_session, employee.id, "old laptop")
    device_service.revoke(db_session, device.id, employee.id)

    res = app_client.post(
        "/telemetry/events",
        json={
            "employee_id": employee.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features": {"active_minutes": 30},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401


def test_a_deactivated_employees_laptop_stops_reporting(app_client, db_session, org):
    """Deactivating a leaver has to stop their machine too, not only stop
    them logging in."""
    employee = make_user(db_session, org, "employee", "agent_left", "agent_left@example.com")
    headers = device_headers(db_session, employee)
    employee.is_active = False
    db_session.commit()

    res = app_client.post(
        "/telemetry/events",
        json={
            "employee_id": employee.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features": {"active_minutes": 30},
        },
        headers=headers,
    )
    assert res.status_code == 401
