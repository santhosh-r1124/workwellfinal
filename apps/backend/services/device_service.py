"""Per-device credentials for the desktop agent.

The plaintext token is returned exactly once, at provisioning, and never
stored. If an employee loses it they provision another and revoke the old
one - which is also the answer to a lost laptop, and the reason the
device list is on the employee's own Privacy Centre rather than buried in
an admin screen. Seeing which machines are reporting about you is itself
a privacy control.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import DeviceToken

# A recognisable prefix so a token that turns up in a log, a support
# ticket or a public repository can be identified and revoked without
# anyone having to work out what it is.
TOKEN_PREFIX = "wwd_"
TOKEN_BYTES = 32
MAX_DEVICES_PER_EMPLOYEE = 10


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def provision(db: Session, employee_id: str, label: str) -> tuple[DeviceToken, str]:
    token = TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_BYTES)
    row = DeviceToken(employee_id=employee_id, label=label.strip() or "Unnamed device", token_hash=hash_token(token))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, token


def authenticate(db: Session, token: str) -> DeviceToken | None:
    """Returns the device this token belongs to, or None.

    Looks up by digest rather than comparing candidates, so the work is a
    single indexed lookup regardless of how many devices exist and there
    is no per-record comparison to time.
    """
    if not token:
        return None

    device = db.scalar(select(DeviceToken).where(DeviceToken.token_hash == hash_token(token)))
    if device is None or device.revoked_at is not None:
        return None

    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return device


def list_for_employee(db: Session, employee_id: str) -> list[DeviceToken]:
    stmt = (
        select(DeviceToken)
        .where(DeviceToken.employee_id == employee_id, DeviceToken.revoked_at.is_(None))
        .order_by(DeviceToken.created_at.desc())
    )
    return list(db.scalars(stmt))


def active_count(db: Session, employee_id: str) -> int:
    return len(list_for_employee(db, employee_id))


def revoke(db: Session, device_id: str, employee_id: str) -> bool:
    """Scoped to the owner: a device id alone must never be enough to cut
    off someone else's machine."""
    device = db.get(DeviceToken, device_id)
    if device is None or device.employee_id != employee_id or device.revoked_at is not None:
        return False
    device.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True
