"""Employee-owned connections to outside sources.

The connector framework and a working ICS calendar client already existed;
nothing could drive them. There was no route, nowhere to keep a person's
subscribe URL, and no schedule - so the one connector that needs no OAuth
and no admin approval, the one that makes the free path complete, sat
unreachable behind a service function.

Two rules shape this module:

* The employee configures it, not an administrator. The credential grants
  access to their calendar; nobody else should be able to attach one on
  their behalf, and they must be able to remove it without asking.
* Consent still decides. A connector is gated by the same source the
  desktop agent is, so connecting a calendar while `calendar_metadata` is
  off collects nothing - and says so, rather than appearing to work.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.core.crypto import UndecryptableSecret, decrypt_dict, encrypt_dict, redact
from apps.backend.models import ConnectorConfig
from apps.backend.services import integration_service, telemetry_service
from integrations import get_connector

logger = logging.getLogger("workwell.connectors")

# How far back a sync reaches. Enough to fill in a gap after a few days
# offline, short enough that a daily sync stays cheap.
SYNC_LOOKBACK_DAYS = 14


def _hint_for(connector_key: str, config: dict) -> str:
    connector = get_connector(connector_key)
    if connector is None:
        return ""
    for field in connector.metadata.required_config:
        value = config.get(field)
        if isinstance(value, str) and value:
            return redact(value, keep=8)
    return ""


def get_config(db: Session, employee_id: str, connector_key: str) -> ConnectorConfig | None:
    return db.scalar(
        select(ConnectorConfig).where(
            ConnectorConfig.employee_id == employee_id,
            ConnectorConfig.connector_key == connector_key,
        )
    )


def list_for_employee(db: Session, employee_id: str) -> list[ConnectorConfig]:
    return list(
        db.scalars(
            select(ConnectorConfig)
            .where(ConnectorConfig.employee_id == employee_id)
            .order_by(ConnectorConfig.connector_key)
        )
    )


def save_config(db: Session, employee_id: str, connector_key: str, config: dict) -> ConnectorConfig:
    row = get_config(db, employee_id, connector_key)
    encrypted = encrypt_dict(config)
    hint = _hint_for(connector_key, config)

    if row is None:
        row = ConnectorConfig(
            employee_id=employee_id,
            connector_key=connector_key,
            encrypted_config=encrypted,
            config_hint=hint,
        )
        db.add(row)
    else:
        row.encrypted_config = encrypted
        row.config_hint = hint
        row.enabled = True
        # A reconfigure clears the previous verdict: whatever went wrong
        # last time may be exactly what this is fixing.
        row.last_sync_status = None
        row.last_sync_detail = None

    db.commit()
    db.refresh(row)
    return row


def remove_config(db: Session, employee_id: str, connector_key: str) -> bool:
    row = get_config(db, employee_id, connector_key)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def _record(db: Session, row: ConnectorConfig, status: str, detail: str | None) -> None:
    row.last_sync_at = datetime.now(timezone.utc)
    row.last_sync_status = status
    # Truncated, and only ever an error class or a short message - never a
    # URL, which is the credential itself.
    row.last_sync_detail = detail[:300] if detail else None
    db.commit()


def sync_one(db: Session, employee_id: str, connector_key: str) -> dict:
    """Pulls the recent window and ingests it as telemetry.

    Never raises for an expected failure - a calendar URL that has been
    revoked is a state to report on the employee's own screen, not a 500
    and not a dead worker job.
    """
    row = get_config(db, employee_id, connector_key)
    if row is None or not row.enabled:
        return {"connector": connector_key, "status": "not_configured", "ingested_days": 0}

    try:
        config = decrypt_dict(row.encrypted_config)
    except UndecryptableSecret:
        _record(db, row, "needs_reconnect", "stored credential could not be read")
        logger.warning("connector %s for one employee needs reconnecting", connector_key)
        return {"connector": connector_key, "status": "needs_reconnect", "ingested_days": 0}

    end = date.today()
    start = end - timedelta(days=SYNC_LOOKBACK_DAYS)

    try:
        result = integration_service.sync_connector(
            db, connector_key, config, employee_id, start, end
        )
    except Exception as exc:
        detail = getattr(exc, "detail", None) or type(exc).__name__
        _record(db, row, "failed", str(detail))
        logger.warning("connector %s sync failed: %s", connector_key, type(exc).__name__)
        return {"connector": connector_key, "status": "failed", "ingested_days": 0}

    if result.get("skipped_reason"):
        # Consent is off. Not an error, and the wording must not imply the
        # employee did something wrong.
        _record(db, row, "consent_off", result["skipped_reason"])
        return {"connector": connector_key, "status": "consent_off", "ingested_days": 0}

    _record(db, row, "ok", None)
    return {
        "connector": connector_key,
        "status": "ok",
        "ingested_days": result.get("ingested_days", 0),
    }


def sync_all_for_employee(db: Session, employee_id: str) -> list[dict]:
    return [sync_one(db, employee_id, row.connector_key) for row in list_for_employee(db, employee_id)]


def employees_with_connectors(db: Session) -> list[str]:
    rows = db.scalars(
        select(ConnectorConfig.employee_id).where(ConnectorConfig.enabled.is_(True)).distinct()
    )
    return list(rows)


def describe(db: Session, employee_id: str) -> list[dict]:
    """What the Privacy Centre shows: every connector the build knows
    about, whether this person has connected it, and how the last sync
    went. Never the credential."""
    configured = {row.connector_key: row for row in list_for_employee(db, employee_id)}
    consents = telemetry_service.consent_map(db, employee_id)

    described = []
    for connector in integration_service.list_connectors():
        row = configured.get(connector["key"])
        described.append(
            {
                **connector,
                "connected": row is not None,
                "config_hint": row.config_hint if row else None,
                "last_sync_at": row.last_sync_at.isoformat() if row and row.last_sync_at else None,
                "last_sync_status": row.last_sync_status if row else None,
                "last_sync_detail": row.last_sync_detail if row else None,
                "consent_enabled": consents.get(connector["consent_source"], False),
            }
        )
    return described
