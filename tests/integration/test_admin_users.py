"""Deactivating someone who has left.

Without this the system keeps analysing ex-employees indefinitely, which
is both useless and outside the consent they gave.
"""

from tests.integration.conftest import auth_headers, make_user


def test_an_admin_can_see_the_org_roster(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "roster_admin", "roster_admin@example.com")
    make_user(db_session, org, "employee", "roster_emp", "roster_emp@example.com")
    headers = auth_headers(app_client, admin.email)

    users = app_client.get("/admin/users", headers=headers).json()["users"]

    emails = {u["email"] for u in users}
    assert "roster_emp@example.com" in emails
    assert all(u["is_active"] for u in users)


def test_a_deactivated_employee_can_no_longer_log_in(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "deact_admin", "deact_admin@example.com")
    employee = make_user(db_session, org, "employee", "deact_emp", "deact_emp@example.com")
    admin_headers = auth_headers(app_client, admin.email)

    res = app_client.patch(
        f"/admin/users/{employee.id}", json={"is_active": False}, headers=admin_headers
    )
    assert res.status_code == 200

    login = app_client.post("/auth/login", json={"email": employee.email, "password": "pw12345"})
    assert login.status_code == 401
    # Deliberately indistinguishable from a wrong password: whether an
    # account exists and is merely deactivated is not something an
    # unauthenticated caller should be able to probe.
    assert login.json()["detail"] == "Invalid credentials"


def test_deactivation_invalidates_a_token_that_was_already_issued(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "tok_admin", "tok_admin@example.com")
    employee = make_user(db_session, org, "employee", "tok_emp", "tok_emp@example.com")
    employee_headers = auth_headers(app_client, employee.email)
    assert app_client.get("/auth/me", headers=employee_headers).status_code == 200

    app_client.patch(
        f"/admin/users/{employee.id}",
        json={"is_active": False},
        headers=auth_headers(app_client, admin.email),
    )

    assert app_client.get("/auth/me", headers=employee_headers).status_code == 401


def test_an_admin_cannot_lock_themselves_out(app_client, db_session, org):
    admin = make_user(db_session, org, "admin", "self_admin", "self_admin@example.com")
    headers = auth_headers(app_client, admin.email)

    res = app_client.patch(f"/admin/users/{admin.id}", json={"is_active": False}, headers=headers)

    assert res.status_code == 400


def test_an_admin_cannot_deactivate_another_orgs_user(app_client, db_session, org):
    from apps.backend.models import Organization

    other_org = Organization(name="Other Co")
    db_session.add(other_org)
    db_session.commit()

    admin = make_user(db_session, org, "admin", "x_admin", "x_admin@example.com")
    outsider = make_user(db_session, other_org, "employee", "x_emp", "x_emp@example.com")

    res = app_client.patch(
        f"/admin/users/{outsider.id}",
        json={"is_active": False},
        headers=auth_headers(app_client, admin.email),
    )

    assert res.status_code == 404


def test_an_employee_cannot_deactivate_anyone(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "noadmin_emp", "noadmin@example.com")
    other = make_user(db_session, org, "employee", "noadmin_other", "noadmin_other@example.com")

    res = app_client.patch(
        f"/admin/users/{other.id}",
        json={"is_active": False},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 403
