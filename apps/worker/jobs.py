"""Job bodies.

Each one takes ids, never feature values, and is idempotent: the queue
delivers at-least-once, so a job that runs twice must be indistinguishable
from a job that ran once. `analyze_employee` gets that from the
intervention cooldown; `apply_retention` from deleting by cutoff date.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from agents.orchestrator import run_orchestration
from apps.backend.models import User
from apps.backend.services import admin_service, connector_service, notification_service

logger = logging.getLogger("workwell.jobs")

HANDLERS: dict[str, Callable[..., dict]] = {}


def job(name: str):
    def register(fn):
        HANDLERS[name] = fn
        return fn

    return register


@job("analyze_employee")
def analyze_employee(db: Session, employee_id: str) -> dict:
    """The whole product loop for one person, off the request path.

    Returns early and cheaply - before any model call - when the employee
    has not consented or has too little history, so the daily sweep can
    enqueue everyone without needing to know who is eligible.
    """
    result = run_orchestration(db, employee_id)

    state = result.get("state")
    if state in ("NO_CONSENT", "INSUFFICIENT_DATA"):
        return {"outcome": state.lower()}

    notified = False
    if result.get("intervention_id"):
        employee = db.get(User, employee_id)
        if employee is not None and employee.notifications_enabled:
            notified = notification_service.notify_intervention_available(
                employee.email, employee_id
            )

    return {
        "outcome": "analyzed",
        "pattern_state": result.get("pattern", {}).get("state"),
        "intervention": result.get("intervention", {}).get("type"),
        "notified": notified,
        "suppressed": result.get("intervention_suppressed", False),
    }


@job("apply_retention")
def apply_retention(db: Session, org_id: str) -> dict:
    """A retention window nobody applies is not a retention window. The
    admin panel has a manual button; this is the same operation on a
    schedule, so the promise made in the Privacy Center holds without
    anyone remembering to click it."""
    result = admin_service.apply_retention(db, org_id)
    logger.info(
        "retention applied: %s daily features, %s telemetry events",
        result.get("daily_features_deleted"),
        result.get("telemetry_events_deleted"),
    )
    return {"outcome": "retained", **result}


@job("sync_connectors")
def sync_connectors(db: Session, employee_id: str) -> dict:
    """Pulls whatever this employee has connected. Idempotent: the window
    is re-ingested each time and telemetry upserts per day, so a repeat
    run overwrites rather than accumulates."""
    results = connector_service.sync_all_for_employee(db, employee_id)
    return {
        "outcome": "synced",
        "connectors": len(results),
        "ingested_days": sum(r.get("ingested_days", 0) for r in results),
        "statuses": sorted({r.get("status", "unknown") for r in results}),
    }


def dispatch(db: Session, job_type: str, args: dict) -> dict:
    handler = HANDLERS.get(job_type)
    if handler is None:
        raise KeyError(f"unknown job type: {job_type}")
    return handler(db, **args)
