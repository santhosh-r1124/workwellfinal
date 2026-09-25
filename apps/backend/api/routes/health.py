"""Three different questions, three endpoints.

`/health/live` asks only whether the process is running: no database, no
Redis, nothing that can fail for a reason a restart would not fix. It is
what a container liveness probe should call - pointing a liveness probe at
a dependency check means a brief Postgres blip restarts every replica,
turning a recoverable outage into an outage plus a thundering herd.

`/health/ready` asks whether this instance can serve traffic, and is what
a load balancer should call. It includes the schema check: a replica
rolled out ahead of its migration is exactly the state that looks healthy
and corrupts data.

`/health` is the human-readable summary of both, and predates them.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.backend.core.config import get_settings
from apps.backend.core.database import get_db
from apps.backend.core.redis_client import get_redis

router = APIRouter(tags=["health"])

MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "database" / "migrations"


def _database_status(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "unavailable"


def _redis_status() -> str:
    try:
        get_redis().ping()
        return "connected"
    except Exception:
        return "unavailable"


def _schema_status(db: Session) -> str:
    """'behind' means this process is running against a database that has
    not had its migrations applied yet."""
    try:
        from alembic.script import ScriptDirectory

        script = ScriptDirectory(str(MIGRATIONS_DIR))
        head = script.get_current_head()
        applied = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        return "unknown"

    if applied is None:
        return "unmigrated"
    return "current" if applied == head else "behind"


def _worker_status() -> str:
    from apps.worker.queue import get_queue

    try:
        queue = get_queue()
        return "running" if queue.worker_alive() else "absent"
    except Exception:
        return "unknown"


@router.get("/health")
def health(db: Session = Depends(get_db)):
    settings = get_settings()

    database_status = _database_status(db)
    redis_status = _redis_status()
    ai_status = "connected" if settings.ai_configured else "not_configured"

    overall = (
        "healthy" if database_status == "connected" and redis_status == "connected" else "degraded"
    )

    return {
        "status": overall,
        "database": database_status,
        "redis": redis_status,
        "ai": ai_status,
        "version": "0.1.0",
    }


@router.get("/health/live")
def live():
    return {"status": "alive", "version": "0.1.0"}


@router.get("/health/ready")
def ready(response: Response, db: Session = Depends(get_db)):
    settings = get_settings()

    database_status = _database_status(db)
    redis_status = _redis_status()
    schema_status = _schema_status(db)
    worker_status = _worker_status()

    # The worker being absent does not make this instance unready: the API
    # still serves stored analyses, and interventions queue up rather than
    # being lost. It is reported so a deployment that forgot the worker is
    # visible instead of quietly analysing nobody.
    serving = (
        database_status == "connected"
        and redis_status == "connected"
        and schema_status in ("current", "unknown")
    )
    response.status_code = 200 if serving else 503

    return {
        "status": "ready" if serving else "not_ready",
        "database": database_status,
        "redis": redis_status,
        "schema": schema_status,
        "worker": worker_status,
        "ai": "connected" if settings.ai_configured else "not_configured",
        "version": "0.1.0",
    }
