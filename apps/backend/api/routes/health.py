from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.backend.core.config import get_settings
from apps.backend.core.database import get_db
from apps.backend.core.redis_client import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    settings = get_settings()

    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "unavailable"

    try:
        get_redis().ping()
        redis_status = "connected"
    except Exception:
        redis_status = "unavailable"

    ai_status = "connected" if settings.ai_configured else "not_configured"

    overall = "healthy" if database_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": overall,
        "database": database_status,
        "redis": redis_status,
        "ai": ai_status,
        "version": "0.1.0",
    }
