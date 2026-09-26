"""What the login screen is allowed to offer.

The first screen of the product used to hardcode three demo accounts and
their shared password. Purge the fixtures - which every install running on
real data should, because invented patterns must not share a database with
measured ones - and that screen carried on offering credentials that no
longer authenticated. It reads as a broken login rather than as a cleaned
database, and it is the first thing anyone sees.
"""

from apps.backend.core.config import get_settings
from shared.constants.demo import DEMO_PASSWORD
from tests.integration.conftest import make_user


def test_a_database_with_no_fixtures_offers_nothing(app_client):
    res = app_client.get("/auth/demo-accounts")

    assert res.status_code == 200
    assert res.json() == []


def test_seeded_fixtures_are_offered_with_the_password_that_opens_them(app_client, db_session, org):
    make_user(db_session, org, "employee", "demo-emp", "employee.a@demo.workwell.ai")

    body = app_client.get("/auth/demo-accounts").json()

    assert [a["email"] for a in body] == ["employee.a@demo.workwell.ai"]
    assert body[0]["password"] == DEMO_PASSWORD


def test_a_real_account_is_never_listed(app_client, db_session, org):
    """The filter is the fixture domain, not a flag someone remembers to
    set. A real employee appearing here would be a credential leak."""
    make_user(db_session, org, "employee", "real-emp", "rowan@northwind.example")
    make_user(db_session, org, "admin", "demo-adm", "admin@demo.workwell.ai")

    emails = [a["email"] for a in app_client.get("/auth/demo-accounts").json()]

    assert emails == ["admin@demo.workwell.ai"]


def test_production_says_nothing_even_when_fixtures_exist(app_client, db_session, org, monkeypatch):
    """A fixture credential is only safe where someone deliberately seeded
    it. Someone seeding demo data into production is a mistake the login
    page should not then advertise to the internet."""
    make_user(db_session, org, "employee", "demo-emp-2", "employee.b@demo.workwell.ai")
    settings = get_settings()
    monkeypatch.setattr(type(settings), "is_production", property(lambda self: True))

    assert app_client.get("/auth/demo-accounts").json() == []


def test_the_offered_accounts_are_ordered_by_what_to_try_first(app_client, db_session, org):
    make_user(db_session, org, "admin", "d-adm", "admin@demo.workwell.ai")
    make_user(db_session, org, "employee", "d-emp", "employee.a@demo.workwell.ai")
    make_user(db_session, org, "manager", "d-mgr", "manager@demo.workwell.ai")

    roles = [a["role"] for a in app_client.get("/auth/demo-accounts").json()]

    assert roles == ["employee", "manager", "admin"]
