"""Google Calendar: sign in with Google, keep only meeting times.

Google is not reachable from the test run, so its two endpoints (token
exchange and events list) are replaced with fakes that answer the way the
real ones do. What is under test is everything on this side of them.
"""

from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from apps.backend.core.config import get_settings
from apps.backend.models import Consent, DailyFeature
from apps.backend.services import connector_service
from integrations import google_calendar
from tests.integration.conftest import auth_headers, make_user

YESTERDAY = date.today() - timedelta(days=1)


@pytest.fixture()
def oauth_client(monkeypatch):
    monkeypatch.setattr(get_settings(), "google_client_id", "test-client.apps.googleusercontent.com")
    monkeypatch.setattr(get_settings(), "google_client_secret", "test-secret")


@pytest.fixture()
def employee(db_session, org):
    user = make_user(db_session, org, "employee", "gcal_emp", "gcal_emp@example.com")
    db_session.add(Consent(user_id=user.id, source="calendar_metadata", enabled=True))
    db_session.commit()
    return user


class FakeGoogle:
    def __init__(self):
        self.events_params = None

    def post(self, url, data=None, timeout=None):
        assert url == google_calendar.TOKEN_URI
        if data["grant_type"] == "authorization_code":
            return httpx.Response(200, json={"access_token": "a1", "refresh_token": "r1"})
        assert data["refresh_token"] == "r1"
        return httpx.Response(200, json={"access_token": "a2"})

    def get(self, url, params=None, headers=None, timeout=None):
        self.events_params = params
        start = datetime.combine(YESTERDAY, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=10)
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "items": [
                    {"start": {"dateTime": start.isoformat()}, "end": {"dateTime": (start + timedelta(minutes=45)).isoformat()}},
                    {"start": {"dateTime": start.isoformat()}, "end": {"dateTime": (start + timedelta(minutes=30)).isoformat()}, "status": "cancelled"},
                    {"start": {"date": YESTERDAY.isoformat()}, "end": {"date": date.today().isoformat()}},
                ]
            },
        )


def test_meeting_minutes_skip_cancelled_free_and_all_day_entries():
    items = [
        {"start": {"dateTime": "2026-10-06T09:00:00+05:30"}, "end": {"dateTime": "2026-10-06T10:00:00+05:30"}},
        {"start": {"dateTime": "2026-10-06T11:00:00+05:30"}, "end": {"dateTime": "2026-10-06T11:30:00+05:30"}, "transparency": "transparent"},
        {"start": {"dateTime": "2026-10-06T12:00:00+05:30"}, "end": {"dateTime": "2026-10-06T12:30:00+05:30"}, "status": "cancelled"},
        {"start": {"date": "2026-10-06"}, "end": {"date": "2026-10-07"}},
    ]
    assert google_calendar.meeting_minutes_from_events(items) == {"2026-10-06": 60.0}


def test_authorize_returns_a_google_consent_url_for_read_only_calendar(app_client, employee, oauth_client):
    res = app_client.get("/me/connectors/google_calendar/authorize", headers=auth_headers(app_client, employee.email))
    assert res.status_code == 200
    q = parse_qs(urlparse(res.json()["url"]).query)
    assert q["scope"] == [google_calendar.SCOPES]
    assert q["access_type"] == ["offline"]
    assert q["redirect_uri"] == [get_settings().google_oauth_redirect_uri]


def test_authorize_without_an_oauth_client_says_so(app_client, employee, monkeypatch):
    monkeypatch.setattr(get_settings(), "google_client_id", "")
    monkeypatch.setattr(get_settings(), "google_client_secret", "")
    monkeypatch.setattr(get_settings(), "google_client_secret_file", "")
    res = app_client.get("/me/connectors/google_calendar/authorize", headers=auth_headers(app_client, employee.email))
    assert res.status_code == 400


def test_callback_stores_the_token_and_pulls_only_meeting_times(app_client, db_session, employee, oauth_client, monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(httpx, "post", fake.post)
    monkeypatch.setattr(httpx, "get", fake.get)

    url = app_client.get(
        "/me/connectors/google_calendar/authorize", headers=auth_headers(app_client, employee.email)
    ).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]

    res = app_client.get(f"/integrations/google/callback?code=c1&state={state}", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"].endswith("/privacy?calendar=connected")

    assert "summary" not in fake.events_params["fields"]
    row = connector_service.get_config(db_session, employee.id, "google_calendar")
    assert row is not None and row.config_hint == "signed in with Google"
    assert "r1" not in row.encrypted_config

    feature = db_session.query(DailyFeature).filter_by(employee_id=employee.id, date=YESTERDAY).one()
    assert feature.meeting_hours == pytest.approx(0.75)


def test_callback_with_a_forged_state_connects_nothing(app_client, db_session, employee, oauth_client):
    res = app_client.get("/integrations/google/callback?code=c1&state=not-a-real-state", follow_redirects=False)
    assert res.headers["location"].endswith("/privacy?calendar=failed")
    assert connector_service.get_config(db_session, employee.id, "google_calendar") is None
