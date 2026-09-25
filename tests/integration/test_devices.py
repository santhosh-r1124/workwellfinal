"""Device provisioning, from the employee's own screen.

Seeing which machines report about you - and being able to cut one off -
is a privacy control, not an administrative detail, which is why these
endpoints live under /me with no employee id in any path.
"""

from apps.backend.models import DeviceToken
from apps.backend.services import device_service
from tests.integration.conftest import auth_headers, make_user


def test_a_provisioned_token_is_shown_once_and_never_stored(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "dev_once", "dev_once@example.com")
    headers = auth_headers(app_client, employee.email)

    created = app_client.post("/me/devices", json={"label": "Work laptop"}, headers=headers).json()
    token = created["token"]

    assert token.startswith(device_service.TOKEN_PREFIX)

    stored = db_session.get(DeviceToken, created["id"])
    assert stored.token_hash != token
    assert token not in stored.token_hash

    listed = app_client.get("/me/devices", headers=headers).json()
    assert [d["label"] for d in listed] == ["Work laptop"]
    assert "token" not in listed[0], "the plaintext must never be readable again"


def test_using_a_device_records_that_it_is_alive(app_client, db_session, org):
    """So an employee can tell a machine that stopped reporting from one
    that never started."""
    from datetime import datetime, timezone

    employee = make_user(db_session, org, "employee", "dev_seen", "dev_seen@example.com")
    device, token = device_service.provision(db_session, employee.id, "laptop")
    assert device.last_seen_at is None

    app_client.post(
        "/telemetry/events",
        json={
            "employee_id": employee.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features": {"active_minutes": 30},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    db_session.refresh(device)
    assert device.last_seen_at is not None


def test_revoking_a_device_removes_it_from_the_list(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "dev_revoke", "dev_revoke@example.com")
    headers = auth_headers(app_client, employee.email)
    created = app_client.post("/me/devices", json={"label": "Old laptop"}, headers=headers).json()

    assert app_client.delete(f"/me/devices/{created['id']}", headers=headers).status_code == 204
    assert app_client.get("/me/devices", headers=headers).json() == []


def test_one_employee_cannot_revoke_anothers_device(app_client, db_session, org):
    """A device id alone must never be enough to cut off someone else's
    machine - which would silently stop their analysis."""
    mine = make_user(db_session, org, "employee", "dev_mine", "dev_mine@example.com")
    theirs = make_user(db_session, org, "employee", "dev_theirs", "dev_theirs@example.com")
    device, _ = device_service.provision(db_session, theirs.id, "their laptop")

    res = app_client.delete(
        f"/me/devices/{device.id}", headers=auth_headers(app_client, mine.email)
    )

    assert res.status_code == 404
    db_session.refresh(device)
    assert device.revoked_at is None


def test_one_employee_cannot_see_anothers_devices(app_client, db_session, org):
    mine = make_user(db_session, org, "employee", "dev_list_a", "dev_list_a@example.com")
    theirs = make_user(db_session, org, "employee", "dev_list_b", "dev_list_b@example.com")
    device_service.provision(db_session, theirs.id, "their laptop")

    listed = app_client.get("/me/devices", headers=auth_headers(app_client, mine.email)).json()

    assert listed == []


def test_devices_are_capped_so_a_leaked_login_cannot_mint_endlessly(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "dev_cap", "dev_cap@example.com")
    headers = auth_headers(app_client, employee.email)

    for i in range(device_service.MAX_DEVICES_PER_EMPLOYEE):
        assert (
            app_client.post("/me/devices", json={"label": f"laptop {i}"}, headers=headers).status_code
            == 201
        )

    res = app_client.post("/me/devices", json={"label": "one too many"}, headers=headers)
    assert res.status_code == 400

    # Revoking one frees a slot.
    listed = app_client.get("/me/devices", headers=headers).json()
    app_client.delete(f"/me/devices/{listed[0]['id']}", headers=headers)
    assert app_client.post("/me/devices", json={"label": "replacement"}, headers=headers).status_code == 201


def test_an_unauthenticated_caller_cannot_provision_a_device(app_client):
    assert app_client.post("/me/devices", json={"label": "x"}).status_code == 401
