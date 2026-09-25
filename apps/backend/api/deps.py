from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

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


def authenticated_device(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
):
    """The desktop agent's credential.

    This used to be one shared secret for every install, with the agent
    naming in the request body which employee it was reporting for. That
    meant anyone who could read an agent config - a file on their own
    laptop - could post fabricated telemetry as any colleague, in a
    product whose entire output is a statement about an individual's work
    pattern. Now each device has its own token, bound to one employee,
    and the binding is what decides whose data a request may write.
    """
    from apps.backend.services import device_service

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing device token")

    device = device_service.authenticate(db, authorization.split(" ", 1)[1])
    if device is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked device token")

    owner = db.get(User, device.employee_id)
    if owner is None or not owner.is_active:
        # Deactivating a leaver has to stop their laptop reporting too,
        # not only stop them logging in.
        raise HTTPException(status_code=401, detail="Device belongs to an inactive account")

    return device
