"""Admin toggles that used to be decorative.

`disabled_sources`, `interventions_enabled` and `allowed_integrations`
were stored, returned by the API and rendered in the admin panel - and
consulted by nothing. A privacy switch that does not switch anything is a
compliance answer the product cannot honour, so each of these asserts the
setting changes behaviour, not just state.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select

from apps.backend.models import Intervention, OrgSettings, TelemetryEvent
from apps.backend.services import telemetry_service
from tests.factories import overtime_day, seed_days
from tests.integration.conftest import auth_headers, make_user


@pytest.fixture()
def employee(db_session, org):
    return make_user(db_session, org, "employee", "policy_emp", "policy_emp@example.com")


def _disable(db_session, org, *sources):
    db_session.add(OrgSettings(org_id=org.id, disabled_sources=list(sources)))
    db_session.commit()


def test_an_org_disabled_source_is_stripped_on_ingest(db_session, org, employee):
    _disable(db_session, org, "typing_dynamics")

    telemetry_service.ingest_event(
        db_session,
        employee.id,
        datetime(2026, 2, 15, 10, 0),
        {"active_minutes": 300, "typing_speed": 52.0, "pause_rate": 0.2},
    )

    stored = db_session.scalar(
        select(TelemetryEvent).where(TelemetryEvent.employee_id == employee.id)
    )
    assert "typing_speed" not in stored.features
    assert "pause_rate" not in stored.features
    assert stored.features["active_minutes"] == 300


def test_an_employee_cannot_switch_on_what_the_org_switched_off(app_client, db_session, org, employee):
    _disable(db_session, org, "typing_dynamics")
    headers = auth_headers(app_client, employee.email)

    res = app_client.patch("/consent/typing_dynamics", json={"enabled": True}, headers=headers)

    assert res.status_code == 400
    assert "organization" in res.json()["detail"]


def test_withdrawing_consent_is_always_allowed(app_client, db_session, org, employee):
    """Org policy may only ever subtract collection. An employee must
    never be blocked from turning something off."""
    _disable(db_session, org, "typing_dynamics")
    headers = auth_headers(app_client, employee.email)

    res = app_client.patch("/consent/working_hours", json={"enabled": False}, headers=headers)

    assert res.status_code == 200
    assert res.json()["enabled"] is False


def test_the_privacy_center_distinguishes_never_collected_from_org_disabled(
    app_client, db_session, org, employee
):
    """'WorkWell never collects this' and 'your employer turned this off'
    are different promises and must not read the same."""
    _disable(db_session, org, "typing_dynamics")
    headers = auth_headers(app_client, employee.email)

    sources = {d["key"]: d for d in app_client.get("/consent", headers=headers).json()}

    assert sources["typing_dynamics"]["org_disabled"] is True
    assert sources["typing_dynamics"]["collectible"] is True
    assert sources["typing_dynamics"]["enabled"] is False

    assert sources["webcam"]["collectible"] is False
    assert sources["webcam"]["org_disabled"] is False


def test_disabling_every_behavioral_source_stops_analysis_entirely(db_session, org, employee):
    from agents.orchestrator import run_orchestration

    seed_days(db_session, employee.id, 20, overtime_day)
    _disable(
        db_session,
        org,
        "working_hours",
        "break_patterns",
        "application_categories",
        "typing_dynamics",
    )

    result = run_orchestration(db_session, employee.id)

    assert result["state"] == "NO_CONSENT"


def test_observe_only_mode_suppresses_the_nudge_but_not_the_analysis(db_session, org, employee):
    from agents.orchestrator import run_orchestration

    seed_days(db_session, employee.id, 20, overtime_day)
    db_session.add(OrgSettings(org_id=org.id, interventions_enabled=False))
    db_session.commit()

    result = run_orchestration(db_session, employee.id)

    assert result["pattern"]["state"] == "PATTERN_CHANGE"
    assert result["intervention_suppressed"] is True
    assert result["intervention_id"] is None
    assert not db_session.scalars(
        select(Intervention).where(Intervention.employee_id == employee.id)
    ).all()


def test_an_integration_outside_the_allowlist_is_refused(db_session, org, employee):
    from fastapi import HTTPException

    from apps.backend.services import integration_service

    db_session.add(OrgSettings(org_id=org.id, allowed_integrations=["something_else"]))
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        integration_service.sync_connector(
            db_session, "ics_calendar", {}, employee.id, date(2026, 2, 1), date(2026, 2, 5)
        )

    assert exc.value.status_code == 403


def test_an_empty_allowlist_means_no_restriction_not_nothing_allowed(db_session, org):
    """A fresh org's settings row is created with defaults, so reading an
    empty list as 'deny all' would silently block every connector."""
    from apps.backend.services import org_policy

    db_session.add(OrgSettings(org_id=org.id))
    db_session.commit()

    assert org_policy.integration_allowed(db_session, org.id, "ics_calendar") is True
