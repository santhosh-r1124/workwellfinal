"""The worker process.

    python -m apps.worker

Runs N consumer threads plus one maintenance thread. The maintenance
thread does three things on a timer: requeue jobs whose lease expired,
publish queue depth as a gauge, and give the scheduler a chance to enqueue
the daily sweep.

Threads rather than processes because these jobs are almost entirely
waiting - on Postgres and on the model API - so the GIL is not the
constraint, and one process keeps the metrics registry and the connection
pool in one place.

SIGTERM is handled properly: in-flight jobs finish, nothing new is
reserved, and the process exits. A container orchestrator's rolling
restart therefore does not produce half-finished analyses. A job that
outlives the grace period is not lost either - its lease expires and
another worker picks it up.
"""

from __future__ import annotations

import logging
import signal
import threading
import time

from apps.backend.core.config import get_settings
from apps.backend.core.database import session_scope
from apps.backend.core.observability import configure_logging, record_job, record_queue_depth
from apps.backend.core.redis_client import get_redis
from apps.worker.jobs import dispatch
from apps.worker.metrics_server import serve as serve_metrics
from apps.worker.queue import JobQueue, SchedulerLock
from apps.worker.scheduler import tick

logger = logging.getLogger("workwell.worker")

MAINTENANCE_INTERVAL_SECONDS = 30
RESERVE_TIMEOUT_SECONDS = 5


def _renew_lease_while_running(queue: JobQueue, job, stop: threading.Event) -> threading.Thread:
    """Hold the reservation for as long as the job is actually running.

    Without this, a job that outlives its lease is reaped and run again
    while the first copy is still going. Delivery is at-least-once and the
    job bodies are idempotent, so that is not a correctness problem - but
    it spends a second set of model calls, which on a rate-limited free
    tier is the one resource there is not enough of. Renewing at a third
    of the lease leaves room for two missed renewals before it lapses.
    """
    interval = max(5.0, queue._lease_seconds / 3)

    def renew() -> None:
        while not stop.wait(interval):
            try:
                queue.extend_lease(job)
            except Exception:
                # Redis is unreachable; the lease will lapse and the job
                # will be retried, which is the designed fallback.
                logger.warning("could not renew lease for %s", job.type)
                return

    thread = threading.Thread(target=renew, name=f"lease-{job.id[:8]}", daemon=True)
    thread.start()
    return thread


def consume_once(queue: JobQueue, timeout: int = RESERVE_TIMEOUT_SECONDS) -> bool:
    """Reserve and run a single job. Returns False when nothing was waiting.

    Exposed separately from the loop so tests can drive exactly one job
    without racing a thread.
    """
    job = queue.reserve(timeout_seconds=timeout)
    if job is None:
        return False

    started = time.perf_counter()
    stop_renewing = threading.Event()
    _renew_lease_while_running(queue, job, stop_renewing)

    try:
        with session_scope() as db:
            result = dispatch(db, job.type, job.args)
    except Exception as exc:
        elapsed = time.perf_counter() - started
        stop_renewing.set()
        retrying = queue.fail(job, f"{type(exc).__name__}: {exc}")
        record_job(job.type, "retried" if retrying else "dead_lettered", elapsed)
        logger.exception("job failed: %s (retrying=%s)", job.type, retrying)
        return True

    stop_renewing.set()
    queue.ack(job)
    record_job(job.type, "succeeded", time.perf_counter() - started)
    logger.info("job done: %s %s", job.type, result.get("outcome", ""))
    return True


def consumer_loop(queue: JobQueue, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            consume_once(queue)
        except Exception:
            # Reaching here means the queue itself is unreachable (Redis
            # down). Back off rather than spinning a hot loop of failures.
            logger.exception("consumer loop error")
            stop.wait(5)


def maintenance_loop(queue: JobQueue, lock: SchedulerLock, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            queue.heartbeat()
            queue.reap_expired()
            record_queue_depth(queue.depth(), queue.in_flight())
            with session_scope() as db:
                tick(queue, lock, db)
        except Exception:
            logger.exception("maintenance loop error")
        stop.wait(MAINTENANCE_INTERVAL_SECONDS)


def main() -> int:
    configure_logging()
    settings = get_settings()

    if not settings.ai_configured and not settings.is_test:
        # Same guard as the API: a worker that starts without a key would
        # run every analysis in permanently degraded narration and look
        # healthy doing it.
        logger.error("GEMINI_API_KEY is not set; refusing to start")
        return 1

    redis_client = get_redis()
    queue = JobQueue(
        redis_client,
        lease_seconds=settings.job_lease_seconds,
        max_attempts=settings.job_max_attempts,
    )
    lock = SchedulerLock(redis_client)
    stop = threading.Event()

    metrics_server = serve_metrics(settings.worker_metrics_port)

    def handle_signal(signum, _frame):
        logger.info("received signal %s, finishing in-flight work", signum)
        stop.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    threads = [
        threading.Thread(target=maintenance_loop, args=(queue, lock, stop), name="maintenance")
    ]
    threads += [
        threading.Thread(target=consumer_loop, args=(queue, stop), name=f"consumer-{i}")
        for i in range(max(1, settings.worker_concurrency))
    ]

    for thread in threads:
        thread.daemon = False
        thread.start()

    logger.info(
        "worker started: %s consumers, daily sweep at %02d:00 UTC",
        settings.worker_concurrency,
        settings.daily_analysis_hour_utc,
    )

    for thread in threads:
        thread.join()

    if metrics_server is not None:
        metrics_server.shutdown()

    logger.info("worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
