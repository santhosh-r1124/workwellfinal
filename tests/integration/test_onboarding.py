"""Setting up a real organisation.

Until this existed the only path to a user was the demo seed - seven
fixtures on @demo.workwell.ai sharing a password printed in the README -
so there was no way to run this product for real, only to look at it.
"""

import pytest
from sqlalchemy import select

from apps.backend.models import AuditLog, Organization, User
from apps.backend.services import onboarding_service
from tests.integration.conftest import auth_headers, make_user


def test_a_new_organisation_gets_one_admin_and_a_generated_password(db_session):
    org, admin, password = onboarding_service.create_organization(
        db_session, "Acme Ltd", "sam@acme.example", "Sam Okafor"
    )

    assert org.name == "Acme Ltd"
    assert admin.email == "sam@acme.example"
    assert len(password) >= 16
    # Generated, not stored: the hash must not be the password.
    assert password not in admin.hashed_password


def test_the_generated_password_actually_works(app_client, db_session):
    _, admin, password = onboarding_service.create_organization(
        db_session, "Acme Two", "boot@acme.example", ""
    )

    res = app_client.post("/auth/login", json={"email": admin.email, "password": password})

    assert res.status_code == 200, res.text


def test_passwords_avoid_characters_nobody_can_transcribe():
    """This gets read off a screen and typed. A bootstrap credential
    nobody can transcribe gets replaced with 'admin'."""
    for _ in range(20):
        assert not set(onboarding_service.generate_password()) & set("O0oIl1")


def test_two_organisations_cannot_share_a_name(db_session):
    onboarding_service.create_organization(db_session, "Duplicate Co", "a@dup.example", "")

    with pytest.raises(onboarding_service.OnboardingError, match="already exists"):
        onboarding_service.create_organization(db_session, "duplicate co", "b@dup.example", "")


def test_an_email_can_only_have_one_account(db_session):
    onboarding_service.create_organization(db_session, "First Co", "same@x.example", "")

    with pytest.raises(onboarding_service.OnboardingError, match="already has an account"):
        onboarding_service.create_organization(db_session, "Second Co", "SAME@x.example", "")


def test_an_admin_can_add_a_colleague(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "onb_admin", "onb_admin@example.com")

    res = app_client.post(
        "/admin/users",
        json={"email": "new.person@acme.example", "full_name": "New Person", "role": "employee",
              "team": "Engineering"},
        headers=auth_headers(app_client, admin.email),
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "new.person@acme.example"

    person = db_session.scalar(select(User).where(User.email == "new.person@acme.example"))
    assert person.org_id == org.id
    assert person.team == "Engineering"

    # And the password they were handed works.
    assert app_client.post(
        "/auth/login", json={"email": person.email, "password": body["password"]}
    ).status_code == 200


def test_the_one_time_password_never_reaches_the_audit_log(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "onb_audit", "onb_audit@example.com")

    body = app_client.post(
        "/admin/users",
        json={"email": "audited@acme.example", "role": "employee"},
        headers=auth_headers(app_client, admin.email),
    ).json()

    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "admin.user_created")).all()
    assert logs
    assert all(body["password"] not in str(log.meta) for log in logs)


def test_a_new_person_lands_in_the_admins_own_organisation(app_client, db_session, org):
    """Not a parameter the caller supplies: an admin adding someone to
    another tenant is the mistake this forecloses."""
    other = Organization(name="Somewhere Else")
    db_session.add(other)
    db_session.commit()

    admin = make_user(db_session, org, "admin", "onb_scope", "onb_scope@example.com")
    res = app_client.post(
        "/admin/users",
        json={"email": "scoped@acme.example", "role": "employee"},
        headers=auth_headers(app_client, admin.email),
    )

    person = db_session.scalar(select(User).where(User.email == "scoped@acme.example"))
    assert res.status_code == 201
    assert person.org_id == org.id
    assert person.org_id != other.id


def test_an_employee_cannot_create_accounts(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "onb_emp", "onb_emp@example.com")

    res = app_client.post(
        "/admin/users",
        json={"email": "sneaky@acme.example", "role": "admin"},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 403


def test_a_duplicate_email_is_refused_with_a_reason(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "onb_dupe", "onb_dupe@example.com")
    headers = auth_headers(app_client, admin.email)
    app_client.post("/admin/users", json={"email": "twice@acme.example"}, headers=headers)

    res = app_client.post("/admin/users", json={"email": "twice@acme.example"}, headers=headers)

    assert res.status_code == 400
    assert "already has an account" in res.json()["detail"]


def test_someone_can_change_the_password_an_admin_handed_them(app_client, db_session, org):
    """Otherwise every account stays on a password its administrator has
    seen - which is every account, since that is how people get added."""
    admin = make_user(db_session, org, "admin", "pw_admin", "pw_admin@example.com")
    created = app_client.post(
        "/admin/users",
        json={"email": "changer@acme.example"},
        headers=auth_headers(app_client, admin.email),
    ).json()

    token = app_client.post(
        "/auth/login", json={"email": "changer@acme.example", "password": created["password"]}
    ).json()["access_token"]

    res = app_client.post(
        "/me/password",
        json={"current_password": created["password"], "new_password": "a much longer passphrase"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 204
    assert app_client.post(
        "/auth/login", json={"email": "changer@acme.example", "password": created["password"]}
    ).status_code == 401
    assert app_client.post(
        "/auth/login",
        json={"email": "changer@acme.example", "password": "a much longer passphrase"},
    ).status_code == 200


def test_changing_a_password_requires_the_current_one(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "pw_wrong", "pw_wrong@example.com")

    res = app_client.post(
        "/me/password",
        json={"current_password": "not-it", "new_password": "a much longer passphrase"},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 400


def test_a_short_new_password_is_refused(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "pw_short", "pw_short@example.com")

    res = app_client.post(
        "/me/password",
        json={"current_password": "pw12345", "new_password": "short"},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 422
