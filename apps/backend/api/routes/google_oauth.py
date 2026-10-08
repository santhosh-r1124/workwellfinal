"""Google sign-in for the Google Calendar connector.

The employee starts it from the Privacy Centre; Google sends them back to
/integrations/google/callback with a one-time code, which is exchanged
here for a refresh token. The `state` parameter is a short-lived signed
token naming the employee, so the callback (which arrives without the
app's bearer token) can only attach a calendar to the person who asked.
"""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.core.config import get_settings
from apps.backend.models import User
from apps.backend.services import connector_service
from integrations import google_calendar
from integrations.base import ConnectorNotConfigured

router = APIRouter(tags=["integrations"])

_STATE_PURPOSE = "google_calendar_connect"


def _state_for(user_id: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=10)
    return jwt.encode({"sub": user_id, "purpose": _STATE_PURPOSE, "exp": exp}, s.app_secret_key, algorithm=s.jwt_algorithm)


def _user_from_state(state: str) -> str | None:
    s = get_settings()
    try:
        claims = jwt.decode(state, s.app_secret_key, algorithms=[s.jwt_algorithm])
    except JWTError:
        return None
    return claims.get("sub") if claims.get("purpose") == _STATE_PURPOSE else None


def _back_to_app(result: str) -> RedirectResponse:
    base = get_settings().app_base_url.rstrip("/")
    return RedirectResponse(f"{base}/privacy?calendar={result}", status_code=302)


@router.get("/me/connectors/google_calendar/authorize")
def authorize(user: User = Depends(get_current_user)):
    try:
        client_id, _ = google_calendar.client_credentials()
    except ConnectorNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    params = {
        "client_id": client_id,
        "redirect_uri": get_settings().google_oauth_redirect_uri,
        "response_type": "code",
        "scope": google_calendar.SCOPES,
        "access_type": "offline",
        # Always ask, so Google always returns a refresh token - without
        # one the connection would stop working after an hour.
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": _state_for(user.id),
    }
    return {"url": f"{google_calendar.AUTH_URI}?{urlencode(params)}"}


@router.get("/integrations/google/callback")
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    user_id = _user_from_state(state or "")
    if error or not code or not user_id or db.get(User, user_id) is None:
        return _back_to_app("cancelled" if error else "failed")

    try:
        client_id, client_secret = google_calendar.client_credentials()
        resp = httpx.post(
            google_calendar.TOKEN_URI,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": get_settings().google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
    except (ConnectorNotConfigured, httpx.HTTPError):
        return _back_to_app("failed")
    if resp.status_code != 200 or not resp.json().get("refresh_token"):
        return _back_to_app("failed")

    connector_service.save_config(
        db, user_id, "google_calendar", {"refresh_token": resp.json()["refresh_token"]}
    )
    result = connector_service.sync_one(db, user_id, "google_calendar")
    return _back_to_app("connected" if result["status"] in ("ok", "consent_off") else "sync_failed")
