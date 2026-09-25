"""A small reliable job queue on Redis.

Why this and not Celery/RQ/Arq: the job set here is fixed and tiny - one
analysis per employee per day plus a nightly retention sweep - and the
queue has to be auditable in a product whose whole claim is that it does
not do anything behind the employee's back. Three hundred lines of
explicit Redis commands are easier to reason about, and to test against a
real Redis, than a framework's worker lifecycle. `docs/deployment.md` says
when to swap it out: if job volume ever justifies fan-out across machines,
or jobs start needing chaining/retries with backoff curves, take the
dependency.

Delivery is at-least-once, which is why every job body must be idempotent.
The pattern is the standard reliable-queue one:

    LPUSH pending                      enqueue
    BRPOPLPUSH pending -> processing   reserve (atomic, blocking)
    SET lease:<id> EX visibility       the reservation's heartbeat
    LREM processing <payload>          ack

A worker that dies mid-job leaves its payload in `processing` with no
lease key; `reap_expired` moves it back. That is the only way a job is
retried, so a job that hangs forever is bounded by the lease, not by the
worker's own liveness.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import redis

logger = logging.getLogger("workwell.queue")

PENDING_KEY = "workwell:jobs:pending"
PROCESSING_KEY = "workwell:jobs:processing"
DEAD_KEY = "workwell:jobs:dead"
LEASE_PREFIX = "workwell:jobs:lease:"
DEDUPE_PREFIX = "workwell:jobs:dedupe:"
HEARTBEAT_KEY = "workwell:worker:heartbeat"
HEARTBEAT_TTL_SECONDS = 90

DEFAULT_LEASE_SECONDS = 300
DEFAULT_MAX_ATTEMPTS = 3
DEAD_LETTER_CAP = 500


@dataclass
class Job:
    type: str
    args: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    attempts: int = 0
    enqueued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dedupe_key: str | None = None

    def to_json(self) -> str:
        # sort_keys matters: the payload string is the identity used by LREM
        # to ack, so it has to serialize identically every time.
        return json.dumps(
            {
                "id": self.id,
                "type": self.type,
                "args": self.args,
                "attempts": self.attempts,
                "enqueued_at": self.enqueued_at,
                "dedupe_key": self.dedupe_key,
            },
            sort_keys=True,
        )

    @staticmethod
    def from_json(raw: str) -> "Job":
        data = json.loads(raw)
        return Job(
            id=data["id"],
            type=data["type"],
            args=data.get("args", {}),
            attempts=data.get("attempts", 0),
            enqueued_at=data.get("enqueued_at", ""),
            dedupe_key=data.get("dedupe_key"),
        )


class JobQueue:
    def __init__(
        self,
        client: redis.Redis,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._redis = client
        self._lease_seconds = lease_seconds
        self._max_attempts = max_attempts

    # -- producing ----------------------------------------------------

    def enqueue(self, job_type: str, dedupe_key: str | None = None, **args) -> str | None:
        """Returns the job id, or None when an identical job is already
        queued. Deduplication is what keeps a retried HTTP request or an
        overlapping scheduler tick from running the same analysis twice;
        the key is released on ack, not on a timer, so the window covers
        the whole run rather than just the wait."""
        job = Job(type=job_type, args=args, dedupe_key=dedupe_key)

        if dedupe_key:
            claimed = self._redis.set(
                DEDUPE_PREFIX + dedupe_key, job.id, nx=True, ex=self._lease_seconds * self._max_attempts
            )
            if not claimed:
                return None

        self._redis.lpush(PENDING_KEY, job.to_json())
        return job.id

    # -- consuming ----------------------------------------------------

    def reserve(self, timeout_seconds: int = 5) -> Job | None:
        raw = self._redis.brpoplpush(PENDING_KEY, PROCESSING_KEY, timeout=timeout_seconds)
        if raw is None:
            return None
        job = Job.from_json(raw)
        self._redis.set(LEASE_PREFIX + job.id, "1", ex=self._lease_seconds)
        return job

    def ack(self, job: Job) -> None:
        pipe = self._redis.pipeline()
        pipe.lrem(PROCESSING_KEY, 1, job.to_json())
        pipe.delete(LEASE_PREFIX + job.id)
        if job.dedupe_key:
            pipe.delete(DEDUPE_PREFIX + job.dedupe_key)
        pipe.execute()

    def fail(self, job: Job, error: str) -> bool:
        """Requeues the job, or dead-letters it once attempts are spent.
        Returns True if it will be retried."""
        pipe = self._redis.pipeline()
        pipe.lrem(PROCESSING_KEY, 1, job.to_json())
        pipe.delete(LEASE_PREFIX + job.id)
        pipe.execute()

        job.attempts += 1
        if job.attempts >= self._max_attempts:
            self._dead_letter(job, error)
            return False

        self._redis.lpush(PENDING_KEY, job.to_json())
        return True

    def _dead_letter(self, job: Job, error: str) -> None:
        # The error string is whatever the job body raised. Job bodies here
        # take ids, never feature values, so this stays free of wellness
        # data - keep it that way if you add a job.
        record = json.dumps(
            {
                "job": json.loads(job.to_json()),
                "error": error[:1000],
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        pipe = self._redis.pipeline()
        pipe.lpush(DEAD_KEY, record)
        pipe.ltrim(DEAD_KEY, 0, DEAD_LETTER_CAP - 1)
        if job.dedupe_key:
            pipe.delete(DEDUPE_PREFIX + job.dedupe_key)
        pipe.execute()
        logger.error("job dead-lettered after %s attempts: %s", job.attempts, job.type)

    # -- recovery -----------------------------------------------------

    def reap_expired(self) -> int:
        """Moves jobs whose lease expired back to pending. A worker killed
        mid-job (deploy, OOM, SIGKILL) leaves exactly this state."""
        requeued = 0
        for raw in self._redis.lrange(PROCESSING_KEY, 0, -1):
            job = Job.from_json(raw)
            if self._redis.exists(LEASE_PREFIX + job.id):
                continue
            removed = self._redis.lrem(PROCESSING_KEY, 1, raw)
            if not removed:
                continue  # another worker got there first
            job.attempts += 1
            if job.attempts >= self._max_attempts:
                self._dead_letter(job, "lease expired without ack")
            else:
                self._redis.lpush(PENDING_KEY, job.to_json())
            requeued += 1
        if requeued:
            logger.warning("requeued %s job(s) with expired leases", requeued)
        return requeued

    def extend_lease(self, job: Job) -> None:
        self._redis.set(LEASE_PREFIX + job.id, "1", ex=self._lease_seconds)

    # -- liveness -----------------------------------------------------

    def heartbeat(self) -> None:
        self._redis.set(HEARTBEAT_KEY, datetime.now(timezone.utc).isoformat(), ex=HEARTBEAT_TTL_SECONDS)

    def worker_alive(self) -> bool:
        """Lets the API tell "queued and about to run" apart from "queued
        and nobody is listening". Without it, a deployment that forgot the
        worker container looks perfectly healthy while quietly never
        analysing anyone."""
        try:
            return bool(self._redis.exists(HEARTBEAT_KEY))
        except Exception:
            return False

    # -- introspection ------------------------------------------------

    def depth(self) -> int:
        return int(self._redis.llen(PENDING_KEY))

    def in_flight(self) -> int:
        return int(self._redis.llen(PROCESSING_KEY))

    def dead_letters(self, limit: int = 20) -> list[dict]:
        return [json.loads(r) for r in self._redis.lrange(DEAD_KEY, 0, limit - 1)]

    def purge(self) -> None:
        """Tests only."""
        keys = [PENDING_KEY, PROCESSING_KEY, DEAD_KEY, HEARTBEAT_KEY]
        keys += list(self._redis.scan_iter(LEASE_PREFIX + "*"))
        keys += list(self._redis.scan_iter(DEDUPE_PREFIX + "*"))
        if keys:
            self._redis.delete(*keys)


class SchedulerLock:
    """One-winner lock so N worker replicas enqueue a daily sweep once
    between them. Deliberately not a general mutex: it is held for the
    whole period it guards (a day), and expiry - not release - is what
    allows the next one."""

    def __init__(self, client: redis.Redis) -> None:
        self._redis = client

    def claim(self, name: str, ttl_seconds: int) -> bool:
        return bool(self._redis.set(f"workwell:sched:{name}", "1", nx=True, ex=ttl_seconds))


def get_queue() -> JobQueue:
    from apps.backend.core.redis_client import get_redis

    return JobQueue(get_redis())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def monotonic() -> float:
    return time.monotonic()
