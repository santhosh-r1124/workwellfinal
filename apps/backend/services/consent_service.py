from fastapi import HTTPException
from sqlalchemy.orm import Session

from apps.backend.models import Consent, ConsentEvent
from apps.backend.repositories import consent_repo
from apps.backend.services import audit_service
from shared.constants.data_sources import DATA_SOURCE_BY_KEY
from shared.enums.data_sources import DataSourceKey
from shared.schemas.consent import DataSourceInfo


def get_catalog_with_state(db: Session, user_id: str) -> list[DataSourceInfo]:
    current = {c.source: c.enabled for c in consent_repo.list_consents(db, user_id)}
    result = []
    for definition in DATA_SOURCE_BY_KEY.values():
        enabled = current.get(definition.key.value, definition.default_enabled)
        if not definition.collectible:
            enabled = False
        result.append(
            DataSourceInfo(
                key=definition.key.value,
                label=definition.label,
                category=definition.category,
                what=definition.what,
                why=definition.why,
                where=definition.where,
                retention=definition.retention,
                who_can_access=definition.who_can_access,
                default_enabled=definition.default_enabled,
                collectible=definition.collectible,
                enabled=enabled,
            )
        )
    return result


def _guard_collectible(source: str) -> None:
    try:
        key = DataSourceKey(source)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown data source '{source}'")
    definition = DATA_SOURCE_BY_KEY[key]
    if not definition.collectible:
        raise HTTPException(
            status_code=400,
            detail=f"'{source}' is never collected by WorkWell, regardless of consent settings.",
        )


def set_consent(db: Session, user_id: str, source: str, enabled: bool) -> Consent:
    _guard_collectible(source)

    existing = consent_repo.get_consent(db, user_id, source)
    previous = existing.enabled if existing else None

    if existing:
        existing.enabled = enabled
        row = existing
    else:
        row = Consent(user_id=user_id, source=source, enabled=enabled)
        db.add(row)

    db.add(
        ConsentEvent(
            user_id=user_id,
            source=source,
            action="update",
            previous_value=previous,
            new_value=enabled,
        )
    )
    db.commit()
    db.refresh(row)

    audit_service.record(
        db,
        actor_id=user_id,
        subject_user_id=user_id,
        action="consent.update",
        resource=f"consent:{source}",
        meta={"previous": previous, "new": enabled},
    )
    return row


def reset_consent(db: Session, user_id: str, source: str) -> Consent:
    try:
        key = DataSourceKey(source)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown data source '{source}'")
    default_enabled = DATA_SOURCE_BY_KEY[key].default_enabled
    return set_consent(db, user_id, source, default_enabled)
