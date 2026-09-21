import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.backend.core.redis_client import get_redis
from apps.backend.middleware.security import (
    AUTH_LIMIT_PER_MINUTE,
    RateLimitMiddleware,
)


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
