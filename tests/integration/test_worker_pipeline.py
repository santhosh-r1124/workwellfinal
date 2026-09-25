"""The product running itself.

This is the loop that was missing: before it, `run_orchestration` was
reachable only from the chat endpoint, so the employee who never opens a
wellbeing dashboard - the one an early-warning system exists for - was
never analysed at all.
"""

import contextlib
from datetime import date, timedelta

import pytest
import redis
from sqlalchemy import select

from apps.backend.core.config import get_settings
from apps.backend.models import AgentRun, Intervention, OrgSettings
from apps.worker import main as worker_main
from apps.worker import scheduler
from apps.worker.queue import JobQueue, SchedulerLock
from tests.factories import overtime_day, seed_days, stable_day
from tests.integration.conftest import make_user

DAY = date(2026, 2, 15)


@pytest.fixture()
def queue():
    client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        client.ping()
    except Exception:
        pytest.skip("redis is not reachable")
    q = JobQueue(client, lease_seconds=30, max_attempts=3)
    q.purge()
    yield q
    q.purge()


@pytest.fixture()
def worker(queue, db_session, monkeypatch):
    """Runs real jobs through the real reserve/dispatch/ack path, against
    the test transaction rather than a fresh connection."""
    monkeypatch.setattr(
        worker_main, "session_scope", lambda: contextlib.nullcontext(db_session)
    )
    return queue


def test_the_daily_sweep_enqueues_one_job_per_employee(queue, db_session, org):
    make_user(db_session, org, "employee", "sweep_a", "sweep_a@example.com")
    make_user(db_session, org, "employee", "sweep_b", "sweep_b@example.com")
    make_user(db_session, org, "admin", "sweep_admin", "sweep_admin@example.com")

    enqueued = scheduler.enqueue_daily_analysis(queue, db_session, DAY)

    assert enqueued == 2, "admins are not analysed; employees are"
    assert queue.depth() == 2


def test_an_employee_who_has_left_is_no_longer_analysed(queue, db_session, org):
    """Continuing to profile someone after they leave is outside the
    consent they gave."""
    staying = make_user(db_session, org, "employee", "sweep_stay", "stay@example.com")
    leaving = make_user(db_session, org, "employee", "sweep_left", "left@example.com")
    leaving.is_active = False
    db_session.commit()

    scheduler.enqueue_daily_analysis(queue, db_session, DAY)

    queued = {queue.reserve(timeout_seconds=1).args["employee_id"] for _ in range(queue.depth() or 1)}
    assert staying.id in queued
    assert leaving.id not in queued


def test_running_the_sweep_twice_in_a_day_does_not_double_the_work(queue, db_session, org):
    make_user(db_session, org, "employee", "sweep_dup", "dup@example.com")

    first = scheduler.enqueue_daily_analysis(queue, db_session, DAY)
    second = scheduler.enqueue_daily_analysis(queue, db_session, DAY)

    assert (first, second) == (1, 0)
    assert queue.depth() == 1


def test_the_sweep_only_runs_at_its_configured_hour(queue, db_session):
    from datetime import datetime, timezone

    settings = get_settings()
    lock = SchedulerLock(queue._redis)
    hour = settings.daily_analysis_hour_utc

    off_hour = datetime(2026, 2, 15, (hour + 5) % 24, tzinfo=timezone.utc)
    assert scheduler.tick(queue, lock, db_session, now=off_hour)["ran"] is False


def test_the_worker_analyses_an_employee_and_proposes_a_nudge(worker, db_session, org):
    employee = make_user(db_session, org, "employee", "worker_ot", "worker_ot@example.com")
    seed_days(db_session, employee.id, 20, overtime_day)

    worker.enqueue("analyze_employee", employee_id=employee.id)
    assert worker_main.consume_once(worker, timeout=1) is True

    run = db_session.scalar(select(AgentRun).where(AgentRun.employee_id == employee.id))
    assert run is not None
    intervention = db_session.scalar(
        select(Intervention).where(Intervention.employee_id == employee.id)
    )
    assert intervention is not None
    assert intervention.type != "no_action"
    assert worker.in_flight() == 0, "a completed job must be acked, not left in flight"


def test_a_stable_employee_gets_an_analysis_but_no_nudge(worker, db_session, org):
    employee = make_user(db_session, org, "employee", "worker_stable", "worker_stable@example.com")
    seed_days(db_session, employee.id, 20, stable_day)

    worker.enqueue("analyze_employee", employee_id=employee.id)
    worker_main.consume_once(worker, timeout=1)

    assert db_session.scalar(select(AgentRun).where(AgentRun.employee_id == employee.id))
    assert not db_session.scalars(
        select(Intervention).where(Intervention.employee_id == employee.id)
    ).all()


def test_the_same_finding_on_consecutive_days_does_not_nudge_twice(worker, db_session, org):
    """A sustained pattern is, by definition, the same finding tomorrow. A
    daily job without a cooldown is a daily notification."""
    employee = make_user(db_session, org, "employee", "worker_cool", "worker_cool@example.com")
    seed_days(db_session, employee.id, 20, overtime_day)

    for _ in range(3):
        worker.enqueue("analyze_employee", employee_id=employee.id)
        worker_main.consume_once(worker, timeout=1)

    interventions = db_session.scalars(
        select(Intervention).where(Intervention.employee_id == employee.id)
    ).all()
    assert len(interventions) == 1

    runs = db_session.scalars(select(AgentRun).where(AgentRun.employee_id == employee.id)).all()
    assert len(runs) == 3, "every run is still recorded; only the nudge is suppressed"


def test_an_observe_only_org_analyses_but_never_nudges(worker, db_session, org):
    """Some rollouts must run silently while a works council reviews them.
    The admin toggle for that previously did nothing at all."""
    employee = make_user(db_session, org, "employee", "worker_quiet", "worker_quiet@example.com")
    seed_days(db_session, employee.id, 20, overtime_day)
    db_session.add(OrgSettings(org_id=org.id, interventions_enabled=False))
    db_session.commit()

    worker.enqueue("analyze_employee", employee_id=employee.id)
    worker_main.consume_once(worker, timeout=1)

    assert db_session.scalar(select(AgentRun).where(AgentRun.employee_id == employee.id))
    assert not db_session.scalars(
        select(Intervention).where(Intervention.employee_id == employee.id)
    ).all()


def test_a_job_for_an_employee_with_no_history_costs_nothing(worker, db_session, org):
    """The sweep enqueues everyone, so a brand new hire is analysed daily.
    That must cost no model call and write no rows - in particular no
    zero-valued baselines, which read as "does no work" rather than "not
    measured yet"."""
    from apps.backend.models import EmployeeBaseline

    employee = make_user(db_session, org, "employee", "worker_empty", "worker_empty@example.com")

    worker.enqueue("analyze_employee", employee_id=employee.id)
    worker_main.consume_once(worker, timeout=1)

    assert not db_session.scalars(select(AgentRun).where(AgentRun.employee_id == employee.id)).all()
    assert not db_session.scalars(
        select(EmployeeBaseline).where(EmployeeBaseline.employee_id == employee.id)
    ).all()
    assert worker.in_flight() == 0


def test_a_job_that_raises_is_retried_and_then_dead_lettered(worker, db_session):
    """A job type that no longer exists - the shape of a bad deploy, where
    a worker rolls out before or after the code that enqueues for it."""
    worker.enqueue("job_type_that_no_longer_exists", employee_id="emp_1")

    for _ in range(3):
        worker_main.consume_once(worker, timeout=1)

    assert worker.depth() == 0
    assert worker.in_flight() == 0
    dead = worker.dead_letters()
    assert len(dead) == 1
    assert dead[0]["job"]["type"] == "job_type_that_no_longer_exists"
    assert "KeyError" in dead[0]["error"]


def test_the_retention_sweep_deletes_past_the_window(worker, db_session, org):
    from apps.backend.models import DailyFeature

    employee = make_user(db_session, org, "employee", "worker_ret", "worker_ret@example.com")
    db_session.add(OrgSettings(org_id=org.id, retention_days=30))
    seed_days(db_session, employee.id, 3, stable_day, end=date.today() - timedelta(days=200))
    seed_days(db_session, employee.id, 3, stable_day, end=date.today())
    db_session.commit()

    worker.enqueue("apply_retention", org_id=org.id)
    worker_main.consume_once(worker, timeout=1)

    remaining = db_session.scalars(
        select(DailyFeature).where(DailyFeature.employee_id == employee.id)
    ).all()
    assert len(remaining) == 3
    assert all(r.date > date.today() - timedelta(days=31) for r in remaining)
