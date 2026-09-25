from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from apps.backend.core.config import get_settings
from apps.backend.core.database import get_db
from apps.backend.core.security import decode_access_token
from apps.backend.models import User
from apps.backend.repositories import user_repo

__all__ = ["get_db"]


def get_current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = user_repo.get_user(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        # Checked per request rather than only at login, so deactivating
        # someone takes effect immediately instead of whenever their
        # existing token happens to expire.
        raise HTTPException(status_code=401, detail="Account is deactivated")
    return user


def require_role(*allowed_roles: str):
    def _checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        from apps.backend.models import Role

        role = db.get(Role, user.role_id)
        if not role or role.name not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _checker


def verify_agent_token(authorization: str | None = Header(default=None)) -> None:
    """Desktop agents authenticate with a single shared device token (the
    app secret key) rather than a per-user login. Real per-device
    provisioning is a Phase 20 hardening item."""
    settings = get_settings()
    expected = f"Bearer {settings.app_secret_key}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid agent token")
