"""Reads analyses; does not produce them.

Until now the only way an analysis came into existence was an employee
sending a chat message, which meant every message paid for a full baseline
recompute over 90 days of history plus three model calls before the
assistant said a word - and meant an employee who never chatted was never
analysed at all.

The producer is now `apps/worker`. This module is the read side: the API
serves the most recent stored run, and asks for a fresh one in the
background when it is old. The one exception is a deployment with no
worker (a single-process pilot, or a developer's laptop), where the first
analysis is computed inline rather than leaving the employee staring at
"queued" forever. That case is detected from the worker's heartbeat rather
than assumed, so a production deployment whose worker has died does not
silently fall back to blocking every request.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from apps.backend.core.config import get_settings
from apps.backend.models import PatternStateRecord
from apps.backend.repositories import agent_repo

logger = logging.getLogger("workwell.analysis")


def _pattern_from_state(record: PatternStateRecord | None) -> dict:
    if record is None:
        return {}
    return {
        "employee_id": record.employee_id,
        "date": record.date.isoformat(),
        "state": record.state,
        "confidence": record.confidence,
        "duration_days": record.duration_days,
        "signals": record.signals or [],
    }


def stored_analysis(db: Session, employee_id: str) -> dict | None:
    run = agent_repo.latest_agent_run(db, employee_id)
    if run is None:
        return None

    pattern_record = db.get(PatternStateRecord, run.pattern_state_id) if run.pattern_state_id else None
    computed_at = run.created_at
    if computed_at is not None and computed_at.tzinfo is None:
        computed_at = computed_at.replace(tzinfo=timezone.utc)

    return {
        "agent_run_id": run.id,
        "employee_id": employee_id,
        "pattern": _pattern_from_state(pattern_record),
        "context": run.context or {},
        "risk": run.risk or {},
        "intervention": run.intervention or {},
        "wellness": run.wellness or {},
        "computed_at": computed_at,
    }


def is_stale(analysis: dict, max_age_hours: int | None = None) -> bool:
    max_age_hours = max_age_hours or get_settings().analysis_max_age_hours
    computed_at = analysis.get("computed_at")
    if computed_at is None:
        return True
    return datetime.now(timezone.utc) - computed_at > timedelta(hours=max_age_hours)


def request_refresh(db: Session, employee_id: str) -> str | None:
    """Fire-and-forget. Returns a job id, or None when the job was already
    queued or the queue is unreachable - neither of which is an error the
    caller should surface, since a stale-but-valid analysis is still
    worth showing."""
    from apps.worker.queue import get_queue

    try:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
        return get_queue().enqueue(
            "analyze_employee",
            dedupe_key=f"analyze:{employee_id}:{stamp}",
            employee_id=employee_id,
        )
    except Exception as exc:
        logger.warning("could not enqueue analysis refresh: %s", type(exc).__name__)
        return None


def live_status(db: Session, employee_id: str) -> dict:
    """A cheap token the client can poll.

    The alternative is polling the dashboard's real payload every few
    seconds - baselines, history, patterns, interventions - which is four
    queries and a render for the common case of nothing having changed.
    This is three cheap lookups and a hash, so the client can refetch only
    when something actually moved.
    """
    from sqlalchemy import func, select

    from apps.backend.models import DailyFeature, Intervention, TelemetryEvent

    latest_run = agent_repo.latest_agent_run(db, employee_id)
    latest_data = db.scalar(
        select(func.max(DailyFeature.created_at)).where(DailyFeature.employee_id == employee_id)
    )
    latest_event = db.scalar(
        select(func.max(TelemetryEvent.timestamp)).where(TelemetryEvent.employee_id == employee_id)
    )
    open_nudges = db.scalar(
        select(func.count(Intervention.id)).where(
            Intervention.employee_id == employee_id, Intervention.status == "proposed"
        )
    )

    token = hashlib.sha256(
        "|".join(
            str(part)
            for part in (
                latest_run.id if latest_run else "",
                latest_run.created_at if latest_run else "",
                latest_data,
                open_nudges,
            )
        ).encode()
    ).hexdigest()[:16]

    return {
        "version": token,
        "analysed_at": latest_run.created_at.isoformat() if latest_run and latest_run.created_at else None,
        "last_data_at": latest_event.isoformat() if latest_event else None,
        "open_interventions": int(open_nudges or 0),
    }


def worker_available() -> bool:
    from apps.worker.queue import get_queue

    try:
        return get_queue().worker_alive()
    except Exception:
        return False


def current_analysis(db: Session, employee_id: str) -> dict | None:
    """What the API should show right now, refreshing in the background if
    what it has is old. Returns None only when there is nothing stored and
    nothing could be computed in time."""
    settings = get_settings()
    analysis = stored_analysis(db, employee_id)

    if analysis is not None and not is_stale(analysis, settings.analysis_max_age_hours):
        return analysis

    request_refresh(db, employee_id)

    if analysis is not None:
        # Stale but real. Showing week-old evidence beats showing nothing,
        # and the refresh is already queued.
        return analysis

    if settings.inline_analysis_fallback and not worker_available():
        from agents.orchestrator import run_orchestration

        logger.info("no worker heartbeat; computing first analysis inline")
        result = run_orchestration(db, employee_id)
        if result.get("state") in ("NO_CONSENT", "INSUFFICIENT_DATA"):
            return result
        return stored_analysis(db, employee_id)

    return None
