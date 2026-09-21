from tests.integration.conftest import auth_headers, make_user


def test_login_and_me(app_client, db_session, org):
    make_user(db_session, org, "employee", "emp_login", "login@example.com")
    headers = auth_headers(app_client, "login@example.com")
    res = app_client.get("/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "login@example.com"


def test_get_consent_reflects_defaults(app_client, db_session, org):
    make_user(db_session, org, "employee", "emp_consent1", "consent1@example.com")
    headers = auth_headers(app_client, "consent1@example.com")

    res = app_client.get("/consent", headers=headers)
    assert res.status_code == 200
    sources = {d["key"]: d for d in res.json()}

    assert sources["working_hours"]["enabled"] is True
    assert sources["calendar_metadata"]["enabled"] is False
    assert sources["webcam"]["enabled"] is False
    assert sources["webcam"]["collectible"] is False


def test_cannot_enable_permanently_disabled_source(app_client, db_session, org):
    make_user(db_session, org, "employee", "emp_consent2", "consent2@example.com")
    headers = auth_headers(app_client, "consent2@example.com")

    res = app_client.patch("/consent/raw_keyboard", json={"enabled": True}, headers=headers)
    assert res.status_code == 400


def test_toggle_consent_persists_and_is_audited(app_client, db_session, org):
    from apps.backend.models import AuditLog

    make_user(db_session, org, "employee", "emp_consent3", "consent3@example.com")
    headers = auth_headers(app_client, "consent3@example.com")

    res = app_client.patch("/consent/typing_dynamics", json={"enabled": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["enabled"] is False

    res2 = app_client.get("/consent", headers=headers)
    updated = {d["key"]: d for d in res2.json()}
    assert updated["typing_dynamics"]["enabled"] is False

    logs = db_session.query(AuditLog).filter_by(subject_user_id="emp_consent3").all()
    assert any(log.action == "consent.update" for log in logs)


def test_reset_consent_returns_to_default(app_client, db_session, org):
    make_user(db_session, org, "employee", "emp_consent4", "consent4@example.com")
    headers = auth_headers(app_client, "consent4@example.com")

    app_client.patch("/consent/working_hours", json={"enabled": False}, headers=headers)
    res = app_client.delete("/consent/working_hours", headers=headers)
    assert res.status_code == 200
    assert res.json()["enabled"] is True
