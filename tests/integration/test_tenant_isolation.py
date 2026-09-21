import pytest

from apps.backend.models import Organization
from tests.integration.conftest import auth_headers, make_user


@pytest.fixture()
def other_org(db_session):
    organization = Organization(name="Other Tenant")
    db_session.add(organization)
    db_session.commit()
    return organization


def test_admin_cannot_read_employee_in_another_org(app_client, db_session, org, other_org):
    """Being an admin somewhere must not grant read access to another
    tenant's employees (Phase 20)."""
    foreign_employee = make_user(
        db_session, other_org, "employee", "foreign_emp", "foreign_emp@example.com"
    )
    make_user(db_session, org, "admin", "tenant_admin", "tenant_admin@example.com")

    headers = auth_headers(app_client, "tenant_admin@example.com")
    res = app_client.get(f"/employees/{foreign_employee.id}/baseline", headers=headers)

    assert res.status_code == 403


def test_admin_can_still_read_own_org_employee(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "own_emp", "own_emp@example.com")
    make_user(db_session, org, "admin", "own_admin", "own_admin@example.com")

    headers = auth_headers(app_client, "own_admin@example.com")
    res = app_client.get(f"/employees/{employee.id}/baseline", headers=headers)

    assert res.status_code == 200


def test_team_analytics_scoped_to_callers_org(app_client, db_session, org, other_org):
    """A manager naming another tenant's team gets their own org's (empty)
    view, never the other tenant's data."""
    for i in range(6):
        member = make_user(
            db_session, other_org, "employee", f"foreign_team_{i}", f"foreign_team_{i}@example.com"
        )
        member.team = "SecretTeam"
    db_session.commit()

    make_user(db_session, org, "manager", "probe_mgr", "probe_mgr@example.com")
    headers = auth_headers(app_client, "probe_mgr@example.com")

    res = app_client.get("/analytics/teams/SecretTeam", headers=headers)
    assert res.status_code == 200
    assert res.json()["cohort_size"] == 0
    assert res.json()["sufficient_cohort"] is False


def test_team_listing_excludes_other_orgs(app_client, db_session, org, other_org):
    foreign = make_user(db_session, other_org, "employee", "foreign_list", "foreign_list@example.com")
    foreign.team = "ForeignOnly"
    local = make_user(db_session, org, "employee", "local_list", "local_list@example.com")
    local.team = "LocalTeam"
    make_user(db_session, org, "manager", "list_mgr", "list_mgr@example.com")
    db_session.commit()

    headers = auth_headers(app_client, "list_mgr@example.com")
    teams = app_client.get("/analytics/teams", headers=headers).json()["teams"]

    assert "LocalTeam" in teams
    assert "ForeignOnly" not in teams
