from apps.backend.core.observability import (
    REGISTRY,
    record_llm_call,
    record_pattern_state,
    render_prometheus,
)
from tests.integration.conftest import auth_headers, make_user


def test_metrics_endpoint_exposes_request_metrics(app_client):
    app_client.get("/health")
    res = app_client.get("/metrics")

    assert res.status_code == 200
    assert "workwell_http_requests_total" in res.text
    assert "workwell_http_request_duration_seconds_bucket" in res.text


def test_request_id_header_is_returned(app_client):
    res = app_client.get("/health")
    assert res.headers.get("X-Request-ID")


def test_supplied_request_id_is_echoed(app_client):
    res = app_client.get("/health", headers={"X-Request-ID": "trace-abc-123"})
    assert res.headers["X-Request-ID"] == "trace-abc-123"


def test_metrics_never_expose_employee_identifiers(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "metrics_emp", "metrics_emp@example.com")
    headers = auth_headers(app_client, "metrics_emp@example.com")

    app_client.get(f"/employees/{employee.id}/baseline", headers=headers)
    res = app_client.get("/metrics")

    # The path label must be the route template, not the populated path.
    assert employee.id not in res.text
    assert "/employees/{employee_id}/baseline" in res.text


def test_counters_render_in_prometheus_format():
    REGISTRY.reset()
    record_pattern_state("PATTERN_CHANGE")
    record_llm_call("local", 0.25)

    output = render_prometheus()
    assert 'workwell_pattern_states_total{state="PATTERN_CHANGE"} 1.0' in output
    assert 'workwell_llm_calls_total{provider="local"} 1.0' in output
    assert "workwell_llm_call_duration_seconds_bucket" in output
    REGISTRY.reset()


def test_security_headers_present_on_responses(app_client):
    res = app_client.get("/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in res.headers
