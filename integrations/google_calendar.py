"""Google Calendar connector.

OAuth 2.0 (the employee signs in with Google and grants read-only calendar
access; the backend keeps only the refresh token, encrypted). Like the ICS
connector, only start and end times leave Google: the events request asks
for those fields alone, so titles, attendees and locations are never even
downloaded. What this module returns is meeting minutes per day.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from integrations.base import ConnectorMetadata, ConnectorNotConfigured, require_config

SCOPES = "https://www.googleapis.com/auth/calendar.readonly"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
EVENTS_URI = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

METADATA = ConnectorMetadata(
    key="google_calendar",
    label="Google Calendar",
    consent_source="calendar_metadata",
    required_config=["refresh_token"],
    auth_kind="oauth2",
    implemented=True,
    notes="Sign in with Google. Reads meeting start and end times only, never titles or attendees.",
)


def client_credentials() -> tuple[str, str]:
    """Client id/secret from GOOGLE_CLIENT_ID/SECRET, or from the downloaded
    OAuth client JSON named by GOOGLE_CLIENT_SECRET_FILE."""
    from apps.backend.core.config import get_settings

    s = get_settings()
    if s.google_client_id and s.google_client_secret:
        return s.google_client_id, s.google_client_secret
    if s.google_client_secret_file and Path(s.google_client_secret_file).is_file():
        data = json.loads(Path(s.google_client_secret_file).read_text())
        block = data.get("installed") or data.get("web") or {}
        if block.get("client_id") and block.get("client_secret"):
            return block["client_id"], block["client_secret"]
    raise ConnectorNotConfigured("Google Calendar is not set up on this server (no OAuth client).")


def is_available() -> bool:
    try:
        client_credentials()
        return True
    except ConnectorNotConfigured:
        return False


def access_token(refresh_token: str) -> str:
    client_id, client_secret = client_credentials()
    resp = httpx.post(
        TOKEN_URI,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    if resp.status_code != 200:
        raise ConnectorNotConfigured("Google rejected the stored sign-in; reconnect the calendar.")
    return resp.json()["access_token"]


def _parse(value: dict) -> datetime | None:
    # All-day entries carry only "date" - holidays and OOO, not meetings.
    stamp = value.get("dateTime")
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def meeting_minutes_from_events(items: list[dict]) -> dict[str, float]:
    per_day: dict[str, float] = {}
    for item in items:
        if item.get("status") == "cancelled" or item.get("transparency") == "transparent":
            continue
        start, end = _parse(item.get("start", {})), _parse(item.get("end", {}))
        if not start or not end or end <= start:
            continue
        key = start.date().isoformat()
        per_day[key] = round(per_day.get(key, 0.0) + (end - start).total_seconds() / 60, 1)
    return per_day


class GoogleCalendarConnector:
    metadata = METADATA

    def is_configured(self, config: dict) -> bool:
        return bool(config.get("refresh_token"))

    def fetch_daily_features(
        self, config: dict, employee_ref: str, start: date, end: date
    ) -> dict[str, dict]:
        require_config(METADATA, config)
        token = access_token(config["refresh_token"])
        params = {
            "timeMin": datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
            "timeMax": datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "2500",
            # Times only: the response never contains event content.
            "fields": "items(start,end,status,transparency),nextPageToken",
        }
        items: list[dict] = []
        while True:
            resp = httpx.get(EVENTS_URI, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            items.extend(body.get("items", []))
            if not body.get("nextPageToken"):
                break
            params["pageToken"] = body["nextPageToken"]

        per_day = meeting_minutes_from_events(items)
        return {d: {"meeting_minutes": m} for d, m in per_day.items() if start.isoformat() <= d <= end.isoformat()}
