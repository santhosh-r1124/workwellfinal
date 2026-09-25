from datetime import date, datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from apps.backend.models import User
from apps.backend.services import org_policy, telemetry_service
from integrations import available_connectors, get_connector
from integrations.base import ConnectorNotConfigured


def list_connectors(db: Session | None = None, org_id: str | None = None) -> list[dict]:
    """`allowed` reflects the org's allowlist. Connectors outside it stay
    visible rather than disappearing: an admin needs to see what exists in
    order to decide to permit it, and a silently missing connector reads
    as a bug."""
    connectors = available_connectors()
    if db is None or org_id is None:
        return [{**c, "allowed": True} for c in connectors]
    return [
        {**c, "allowed": org_policy.integration_allowed(db, org_id, c["key"])}
        for c in connectors
    ]


def sync_connector(
    db: Session,
    connector_key: str,
    config: dict,
    employee_id: str,
    start: date,
    end: date,
    employee_ref: str | None = None,
) -> dict:
    """Pulls a date range from a connector and ingests it as telemetry.

    Consent is checked twice on purpose. Here, against the connector's
    declared consent_source, so a connector is never even called for a
    signal the employee has switched off. Then again inside
    telemetry_service.ingest_event, which strips individual disallowed
    fields before the write. An integration must extend the consent model,
    never route around it.
    """
    connector = get_connector(connector_key)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_key}'")

    employee = db.get(User, employee_id)
    if employee is not None and not org_policy.integration_allowed(
        db, employee.org_id, connector_key
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Connector '{connector_key}' is not on this organization's allowlist.",
        )

    source = connector.metadata.consent_source
    consents = telemetry_service.consent_map(db, employee_id)
    if not consents.get(source, False):
        return {
            "connector": connector_key,
            "ingested_days": 0,
            "skipped_reason": f"employee has not consented to '{source}'",
        }

    try:
        per_day = connector.fetch_daily_features(
            config, employee_ref or employee_id, start, end
        )
    except ConnectorNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ingested = 0
    for iso_day, features in sorted(per_day.items()):
        day = date.fromisoformat(iso_day)
        # Midday timestamp: these are whole-day rollups from an external
        # system, not point-in-time observations, and noon keeps them out of
        # the after-hours window that schedule features key off.
        timestamp = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)
        telemetry_service.ingest_event(db, employee_id, timestamp, features)
        telemetry_service.recompute_daily_feature(db, employee_id, day)
        ingested += 1

    return {"connector": connector_key, "ingested_days": ingested, "skipped_reason": None}
