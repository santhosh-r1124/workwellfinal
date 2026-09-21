def test_health_endpoint_reports_all_dependencies(app_client):
    response = app_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "connected"
    assert body["version"] == "0.1.0"
    assert set(body.keys()) == {"status", "database", "redis", "ai", "version"}
