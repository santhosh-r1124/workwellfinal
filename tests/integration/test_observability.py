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


def test_a_metric_with_several_label_values_declares_its_type_once(app_client):
    """Prometheus rejects a scrape that declares the same metric name
    twice, so emitting TYPE per series - rather than per family - breaks
    the whole endpoint the moment a metric gains a second label value."""
    from apps.backend.core.observability import REGISTRY, render_prometheus

    REGISTRY.reset()
    REGISTRY.increment("workwell_interventions_total", {"type": "focus_block"})
    REGISTRY.increment("workwell_interventions_total", {"type": "recovery_break"})
    REGISTRY.observe("workwell_job_duration_seconds", 0.2, {"type": "analyze_employee"})
    REGISTRY.observe("workwell_job_duration_seconds", 0.4, {"type": "apply_retention"})
    REGISTRY.set_gauge("workwell_job_queue_pending", 3)

    lines = render_prometheus().splitlines()
    type_lines = [line for line in lines if line.startswith("# TYPE")]

    assert len(type_lines) == len(set(type_lines))
    names = [line.split()[2] for line in type_lines]
    assert len(names) == len(set(names)), f"duplicate TYPE declarations: {names}"


def test_queue_depth_is_exposed_on_the_scrape_target(app_client):
    """The worker exports its own metrics, but the case that matters most
    is the worker being down - and therefore exporting nothing."""
    body = app_client.get("/metrics").text
    assert "workwell_job_queue_pending" in body
