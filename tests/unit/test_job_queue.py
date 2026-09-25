"""The queue against a real Redis.

Delivery guarantees are the kind of thing that looks obviously correct in
code and is wrong in practice, so these exercise the failure paths - a
worker dying mid-job, a duplicate enqueue, a job that never stops failing
- rather than only the happy path.
"""

import pytest
import redis

from apps.backend.core.config import get_settings
from apps.worker.queue import (
    DEDUPE_PREFIX,
    LEASE_PREFIX,
    PROCESSING_KEY,
    Job,
    JobQueue,
    SchedulerLock,
)


@pytest.fixture()
def queue():
    client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        client.ping()
    except Exception:
        pytest.skip("redis is not reachable")
    q = JobQueue(client, lease_seconds=5, max_attempts=3)
    q.purge()
    yield q
    q.purge()


def test_enqueue_then_reserve_returns_the_job(queue):
    job_id = queue.enqueue("analyze_employee", employee_id="emp_1")
    assert job_id

    job = queue.reserve(timeout_seconds=1)
    assert job is not None
    assert job.type == "analyze_employee"
    assert job.args == {"employee_id": "emp_1"}
    assert queue.depth() == 0
    assert queue.in_flight() == 1


def test_ack_clears_the_job_from_in_flight(queue):
    queue.enqueue("analyze_employee", employee_id="emp_1")
    job = queue.reserve(timeout_seconds=1)

    queue.ack(job)

    assert queue.in_flight() == 0
    assert queue.depth() == 0


def test_reserve_returns_none_when_nothing_is_queued(queue):
    assert queue.reserve(timeout_seconds=1) is None


def test_a_deduped_job_is_only_queued_once(queue):
    first = queue.enqueue("analyze_employee", dedupe_key="emp_1:2026-02-15", employee_id="emp_1")
    second = queue.enqueue("analyze_employee", dedupe_key="emp_1:2026-02-15", employee_id="emp_1")

    assert first is not None
    assert second is None
    assert queue.depth() == 1


def test_the_dedupe_key_is_released_on_ack_so_the_next_window_can_queue(queue):
    queue.enqueue("analyze_employee", dedupe_key="emp_1:today", employee_id="emp_1")
    job = queue.reserve(timeout_seconds=1)
    queue.ack(job)

    assert queue.enqueue("analyze_employee", dedupe_key="emp_1:today", employee_id="emp_1")


def test_a_failed_job_goes_back_to_the_queue_with_its_attempt_count(queue):
    queue.enqueue("analyze_employee", employee_id="emp_1")
    job = queue.reserve(timeout_seconds=1)

    assert queue.fail(job, "boom") is True
    assert queue.in_flight() == 0
    assert queue.depth() == 1

    retried = queue.reserve(timeout_seconds=1)
    assert retried.attempts == 1
    assert retried.id == job.id


def test_a_job_that_keeps_failing_is_dead_lettered_not_retried_forever(queue):
    queue.enqueue("analyze_employee", employee_id="emp_1")

    for _ in range(2):
        job = queue.reserve(timeout_seconds=1)
        assert queue.fail(job, "boom") is True

    job = queue.reserve(timeout_seconds=1)
    assert queue.fail(job, "boom") is False

    assert queue.depth() == 0
    assert queue.in_flight() == 0
    dead = queue.dead_letters()
    assert len(dead) == 1
    assert dead[0]["error"] == "boom"


def test_a_worker_dying_mid_job_leaves_work_that_gets_requeued(queue):
    """The reservation is only as good as its lease: kill the worker and
    the job must come back, not sit in `processing` forever."""
    queue.enqueue("analyze_employee", employee_id="emp_1")
    job = queue.reserve(timeout_seconds=1)

    # Simulate the worker's process disappearing: the payload stays in
    # `processing`, but nothing is renewing its lease.
    queue._redis.delete(LEASE_PREFIX + job.id)

    assert queue.reap_expired() == 1
    assert queue.in_flight() == 0
    assert queue.depth() == 1
    assert queue.reserve(timeout_seconds=1).attempts == 1


def test_reaping_leaves_jobs_whose_lease_is_still_valid(queue):
    queue.enqueue("analyze_employee", employee_id="emp_1")
    queue.reserve(timeout_seconds=1)

    assert queue.reap_expired() == 0
    assert queue.in_flight() == 1


def test_a_job_payload_round_trips_identically(queue):
    """ack removes by exact payload string, so serialization has to be
    stable - a reordered key would silently leak in-flight entries."""
    job = Job(type="analyze_employee", args={"b": 2, "a": 1})
    assert Job.from_json(job.to_json()).to_json() == job.to_json()


def test_worker_liveness_is_reported_from_the_heartbeat(queue):
    assert queue.worker_alive() is False
    queue.heartbeat()
    assert queue.worker_alive() is True


def test_the_scheduler_lock_admits_exactly_one_claimant(queue):
    lock = SchedulerLock(queue._redis)
    try:
        assert lock.claim("test-day", ttl_seconds=30) is True
        assert lock.claim("test-day", ttl_seconds=30) is False
    finally:
        queue._redis.delete("workwell:sched:test-day")


def test_purge_leaves_no_residue(queue):
    queue.enqueue("analyze_employee", dedupe_key="k", employee_id="emp_1")
    queue.reserve(timeout_seconds=1)

    queue.purge()

    assert queue.depth() == 0
    assert queue.in_flight() == 0
    assert queue._redis.llen(PROCESSING_KEY) == 0
    assert not list(queue._redis.scan_iter(DEDUPE_PREFIX + "*"))


def test_a_long_job_keeps_its_reservation(queue):
    """A job that outlives its lease is reaped and run again while the
    first copy is still going. The bodies are idempotent so that is not a
    correctness problem, but it spends a second set of model calls - the
    one resource a free tier does not have spare."""
    import threading

    from apps.worker.main import _renew_lease_while_running

    queue.enqueue("analyze_employee", employee_id="emp_1")
    job = queue.reserve(timeout_seconds=1)

    # A lease short enough to lapse during the "job".
    queue._lease_seconds = 0.6
    stop = threading.Event()
    _renew_lease_while_running(queue, job, stop)

    try:
        # Longer than the lease: without renewal the reaper would take it.
        threading.Event().wait(1.4)
        assert queue.reap_expired() == 0, "the lease lapsed while the job was still running"
        assert queue.in_flight() == 1
    finally:
        stop.set()


def test_the_renewal_stops_when_the_job_does(queue):
    """Otherwise a finished job's thread keeps a dead reservation alive."""
    import threading

    from apps.worker.main import _renew_lease_while_running

    queue.enqueue("analyze_employee", employee_id="emp_1")
    job = queue.reserve(timeout_seconds=1)
    queue._lease_seconds = 0.6

    stop = threading.Event()
    thread = _renew_lease_while_running(queue, job, stop)
    stop.set()
    thread.join(timeout=3)

    assert not thread.is_alive()
