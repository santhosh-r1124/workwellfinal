"""Liveness, readiness and the schema check.

Pointing a liveness probe at a dependency check means a brief Postgres
blip restarts every replica, turning a recoverable outage into an outage
plus a thundering herd. These endpoints exist so that cannot be
configured by accident.
"""


def test_liveness_touches_no_dependencies(app_client, monkeypatch):
    import apps.backend.api.routes.health as health_module

    def explode(*args, **kwargs):
        raise AssertionError("liveness must not touch a dependency")

    monkeypatch.setattr(health_module, "_database_status", explode)
    monkeypatch.setattr(health_module, "_redis_status", explode)

    res = app_client.get("/health/live")

    assert res.status_code == 200
    assert res.json()["status"] == "alive"


def test_readiness_reports_every_dependency(app_client):
    body = app_client.get("/health/ready").json()

    assert body["status"] == "ready"
    assert body["database"] == "connected"
    assert set(body) == {"status", "database", "redis", "schema", "worker", "ai", "version"}


def test_readiness_fails_closed_when_the_database_is_gone(app_client, monkeypatch):
    import apps.backend.api.routes.health as health_module

    monkeypatch.setattr(health_module, "_database_status", lambda db: "unavailable")

    res = app_client.get("/health/ready")

    assert res.status_code == 503
    assert res.json()["status"] == "not_ready"


def test_a_replica_ahead_of_its_migration_is_not_ready(app_client, monkeypatch):
    """The failure mode this exists for: code rolled out before its
    migration looks perfectly healthy and corrupts data."""
    import apps.backend.api.routes.health as health_module

    monkeypatch.setattr(health_module, "_schema_status", lambda db: "behind")

    res = app_client.get("/health/ready")

    assert res.status_code == 503
    assert res.json()["schema"] == "behind"


def test_a_missing_worker_is_reported_but_does_not_make_the_api_unready(app_client, monkeypatch):
    """The API still serves stored analyses without a worker; jobs queue
    rather than being lost. It is reported so a deployment that forgot the
    worker is visible instead of quietly analysing nobody."""
    import apps.backend.api.routes.health as health_module

    monkeypatch.setattr(health_module, "_worker_status", lambda: "absent")

    res = app_client.get("/health/ready")

    assert res.status_code == 200
    assert res.json()["worker"] == "absent"


def test_the_legacy_health_endpoint_still_answers(app_client):
    body = app_client.get("/health").json()
    assert set(body) == {"status", "database", "redis", "ai", "version"}
