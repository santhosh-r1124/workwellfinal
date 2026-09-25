import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.backend.core.redis_client import get_redis
from apps.backend.middleware.security import (
    AUTH_LIMIT_PER_MINUTE,
    RateLimitMiddleware,
)
from tests.integration.conftest import auth_headers, make_user


@pytest.fixture()
def limited_client():
    """Rate limiting is off under APP_ENV=test so the rest of the suite is
    not throttled, so it gets exercised on a purpose-built app here."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/auth/login")
    def login():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    with TestClient(app) as client:
        yield client


def _unique_token() -> dict:
    return {"Authorization": f"Bearer {uuid.uuid4().hex}"}


def test_auth_endpoint_throttles_after_limit(limited_client):
    headers = _unique_token()

    for _ in range(AUTH_LIMIT_PER_MINUTE):
        assert limited_client.post("/auth/login", headers=headers).status_code == 200

    blocked = limited_client.post("/auth/login", headers=headers)
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"


def test_limits_are_per_identity(limited_client):
    exhausted = _unique_token()
    for _ in range(AUTH_LIMIT_PER_MINUTE + 1):
        limited_client.post("/auth/login", headers=exhausted)

    # A different token must still have its own budget.
    assert limited_client.post("/auth/login", headers=_unique_token()).status_code == 200


def test_health_is_never_rate_limited(limited_client):
    headers = _unique_token()
    for _ in range(AUTH_LIMIT_PER_MINUTE * 3):
        assert limited_client.get("/health", headers=headers).status_code == 200


def test_fails_open_when_redis_is_unavailable(limited_client, monkeypatch):
    """A wellness tool locking employees out because a cache is down is
    worse than briefly losing rate limiting."""
    import apps.backend.middleware.security as security_module

    def _broken_redis():
        raise ConnectionError("redis down")

    monkeypatch.setattr(security_module, "get_redis", _broken_redis)

    headers = _unique_token()
    for _ in range(AUTH_LIMIT_PER_MINUTE + 5):
        assert limited_client.post("/auth/login", headers=headers).status_code == 200

    get_redis.cache_clear()


def test_health_probes_are_never_rate_limited():
    """A liveness probe that gets a 429 is read by the orchestrator as a
    dead container, so rate limiting these turns a traffic burst into a
    rolling restart - the limiter causing the outage it exists to
    prevent."""
    from apps.backend.middleware.security import EXEMPT_PATHS

    assert "/health/live" in EXEMPT_PATHS
    assert "/health/ready" in EXEMPT_PATHS


def test_the_rate_limit_bucket_is_stable_across_processes():
    """Python randomises string hashing per process, so hash() gave the
    same token a different Redis key on every replica and the shared
    budget was silently per-process."""
    import subprocess
    import sys

    program = (
        "from starlette.requests import Request;"
        "from apps.backend.middleware.security import RateLimitMiddleware;"
        "scope={'type':'http','headers':[(b'authorization',b'Bearer abc123')],'client':None};"
        "print(RateLimitMiddleware._identity(Request(scope)))"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", program], capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(3)
    }

    assert len(runs) == 1, f"identity differed between processes: {runs}"
    assert "abc123" not in runs.pop(), "the raw token must not become a Redis key"


def test_an_oversized_chat_message_is_rejected_before_it_reaches_the_model(
    app_client, db_session, org
):
    """An unbounded body is a day's free-tier quota in one request."""
    from shared.schemas.chat import MAX_MESSAGE_CHARS

    employee = make_user(db_session, org, "employee", "rl_chat", "rl_chat@example.com")

    res = app_client.post(
        "/chat",
        json={"employee_id": "", "message": "x" * (MAX_MESSAGE_CHARS + 1)},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 422


def test_an_empty_chat_message_is_rejected(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "rl_empty", "rl_empty@example.com")

    res = app_client.post(
        "/chat",
        json={"employee_id": "", "message": ""},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 422


def test_an_oversized_connector_config_is_rejected(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "rl_conn", "rl_conn@example.com")

    res = app_client.put(
        "/me/connectors/ics_calendar",
        json={"config": {"ics_path_or_url": "x" * 5000}},
        headers=auth_headers(app_client, employee.email),
    )

    assert res.status_code == 422
