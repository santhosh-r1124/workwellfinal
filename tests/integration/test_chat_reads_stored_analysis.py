"""Chat explains an analysis; it does not produce one.

Before this split, every chat message recomputed 90 days of baselines and
made three model calls before the assistant said a word - the product's
slowest operation in front of its most latency-sensitive surface - and
chat could disagree with the dashboard, because each recomputed
independently.
"""

import pytest
import redis
from sqlalchemy import select

from apps.backend.core.config import get_settings
from apps.backend.models import AgentRun, Intervention
from apps.backend.services import analysis_service
from tests.factories import overtime_day, seed_days
from tests.integration.conftest import auth_headers, make_user


@pytest.fixture(autouse=True)
def no_worker_heartbeat():
    """These tests run the single-process path: no worker, so the first
    analysis is computed inline."""
    try:
        client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
        client.delete("workwell:worker:heartbeat")
    except Exception:
        pytest.skip("redis is not reachable")


@pytest.fixture()
def employee_with_history(db_session, org):
    employee = make_user(db_session, org, "employee", "chat_emp", "chat_emp@example.com")
    seed_days(db_session, employee.id, 20, overtime_day)
    return employee


def test_the_first_message_computes_an_analysis_when_there_is_no_worker(
    app_client, db_session, employee_with_history
):
    headers = auth_headers(app_client, employee_with_history.email)

    res = app_client.post("/chat", json={"employee_id": "", "message": "why?"}, headers=headers)

    assert res.status_code == 200
    assert db_session.scalars(
        select(AgentRun).where(AgentRun.employee_id == employee_with_history.id)
    ).all()


def test_later_messages_reuse_the_stored_analysis(app_client, db_session, employee_with_history):
    """The expensive half runs once. Three more questions must not produce
    three more analyses - or three more nudges."""
    headers = auth_headers(app_client, employee_with_history.email)
    app_client.post("/chat", json={"employee_id": "", "message": "why?"}, headers=headers)

    runs_after_first = len(
        db_session.scalars(
            select(AgentRun).where(AgentRun.employee_id == employee_with_history.id)
        ).all()
    )

    for message in ("what should I do?", "is this normal?", "it's because of a release"):
        app_client.post("/chat", json={"employee_id": "", "message": message}, headers=headers)

    runs_after = db_session.scalars(
        select(AgentRun).where(AgentRun.employee_id == employee_with_history.id)
    ).all()
    interventions = db_session.scalars(
        select(Intervention).where(Intervention.employee_id == employee_with_history.id)
    ).all()

    assert len(runs_after) == runs_after_first
    assert len(interventions) <= 1


def test_the_employees_own_words_still_shape_the_answer(
    app_client, db_session, employee_with_history
):
    """Reusing the stored analysis must not cost the employee their voice:
    the note is what the context step consumes."""
    headers = auth_headers(app_client, employee_with_history.email)
    app_client.post("/chat", json={"employee_id": "", "message": "why?"}, headers=headers)

    res = app_client.post(
        "/chat",
        json={"employee_id": "", "message": "it's because of a release"},
        headers=headers,
    )

    assert res.status_code == 200
    assert res.json()["reply"]


def test_the_note_survives_into_the_next_scheduled_run(db_session, employee_with_history):
    """An employee who explains "it's because of a release" should not have
    to explain it again tomorrow - a scheduled run has nobody to ask."""
    from apps.backend.repositories import chat_repo
    from apps.backend.services import chat_service

    chat_service.handle_message(
        db_session, employee_with_history.id, None, "it's because of a release"
    )

    assert (
        chat_repo.latest_employee_note(db_session, employee_with_history.id)
        == "it's because of a release"
    )


def test_a_message_that_trips_the_safety_classifier_is_not_reused_as_context(
    db_session, employee_with_history
):
    """Crisis disclosures belong to the safety pipeline, which is
    deliberately separate. They must never be recycled as workplace
    context for a wellness recommendation."""
    from apps.backend.repositories import chat_repo
    from apps.backend.services import chat_service

    chat_service.handle_message(db_session, employee_with_history.id, None, "I want to kill myself")

    assert chat_repo.latest_employee_note(db_session, employee_with_history.id) is None


def test_an_employee_with_no_history_is_told_it_is_still_building(app_client, db_session, org):
    employee = make_user(db_session, org, "employee", "chat_new", "chat_new@example.com")
    headers = auth_headers(app_client, employee.email)

    res = app_client.post("/chat", json={"employee_id": "", "message": "why?"}, headers=headers)

    assert res.status_code == 200
    assert res.json()["safety_flagged"] is False
    assert res.json()["reply"]


def test_a_stale_analysis_is_still_shown_while_a_refresh_is_queued(
    db_session, employee_with_history, monkeypatch
):
    """Week-old evidence beats a spinner. The refresh happens behind it."""
    from agents.orchestrator import run_orchestration

    run_orchestration(db_session, employee_with_history.id)

    monkeypatch.setattr(analysis_service, "is_stale", lambda *a, **k: True)
    requested = []
    monkeypatch.setattr(
        analysis_service,
        "request_refresh",
        lambda db, employee_id: requested.append(employee_id),
    )

    analysis = analysis_service.current_analysis(db_session, employee_with_history.id)

    assert analysis is not None
    assert analysis["pattern"]["state"] == "PATTERN_CHANGE"
    assert requested == [employee_with_history.id]
