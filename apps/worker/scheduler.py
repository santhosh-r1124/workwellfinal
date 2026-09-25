"""The daily sweep.

Without this, WorkWell only notices a sustained change in someone's work
pattern if that person happens to open the assistant and ask - which
inverts the product: the employee who is heads-down for three weeks and
never opens a wellbeing dashboard is precisely the one an early-warning
system exists for.

Timing is deliberately coarse. There is no benefit to analysing at a
precise instant, and a sweep that lands mid-morning would generate nudges
while people are working. It runs once per calendar day (UTC) at a
configured hour, after most timezones' working day.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.core.config import get_settings
from apps.backend.models import Organization, Role, User
from apps.worker.queue import JobQueue, SchedulerLock
from shared.enums.roles import RoleName

logger = logging.getLogger("workwell.scheduler")

DAY_SECONDS = 86400
# The lock outlives the day it guards so a worker whose clock drifts, or
# which restarts near the boundary, cannot run the sweep twice.
LOCK_TTL_SECONDS = DAY_SECONDS + 3600


def employee_ids(db: Session) -> list[str]:
    """Everyone with the employee role. Eligibility (consent, enough
    history) is decided inside the job, which returns before any model
    call when it is not met - so the sweep does not need to duplicate that
    logic, and cannot drift from it."""
    stmt = (
        select(User.id)
        .join(Role, Role.id == User.role_id)
        .where(Role.name == RoleName.EMPLOYEE.value, User.is_active.is_(True))
    )
    return list(db.scalars(stmt))


def org_ids(db: Session) -> list[str]:
    return list(db.scalars(select(Organization.id)))


def enqueue_daily_analysis(queue: JobQueue, db: Session, day: date) -> int:
    """The dedupe key is employee+day, so a restart mid-sweep resumes
    rather than re-enqueues."""
    enqueued = 0
    for employee_id in employee_ids(db):
        job_id = queue.enqueue(
            "analyze_employee",
            dedupe_key=f"analyze:{employee_id}:{day.isoformat()}",
            employee_id=employee_id,
        )
        if job_id:
            enqueued += 1
    return enqueued


def enqueue_daily_retention(queue: JobQueue, db: Session, day: date) -> int:
    enqueued = 0
    for org_id in org_ids(db):
        job_id = queue.enqueue(
            "apply_retention",
            dedupe_key=f"retention:{org_id}:{day.isoformat()}",
            org_id=org_id,
        )
        if job_id:
            enqueued += 1
    return enqueued


def due(now: datetime, hour_utc: int) -> bool:
    return now.astimezone(timezone.utc).hour == hour_utc


def tick(queue: JobQueue, lock: SchedulerLock, db: Session, now: datetime | None = None) -> dict:
    """Called on a timer by the worker. Safe to call from every replica:
    the Redis lock decides which one actually enqueues, and the dedupe
    keys catch anything that slips past it."""
    settings = get_settings()
    now = now or datetime.now(timezone.utc)

    if not due(now, settings.daily_analysis_hour_utc):
        return {"ran": False, "reason": "not_due"}

    day = now.astimezone(timezone.utc).date()
    if not lock.claim(f"daily:{day.isoformat()}", LOCK_TTL_SECONDS):
        return {"ran": False, "reason": "another_replica_has_it"}

    analyses = enqueue_daily_analysis(queue, db, day)
    retentions = enqueue_daily_retention(queue, db, day)
    logger.info("daily sweep enqueued %s analyses and %s retention jobs", analyses, retentions)
    return {"ran": True, "analyses": analyses, "retention": retentions}
