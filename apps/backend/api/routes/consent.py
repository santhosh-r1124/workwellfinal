from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.models import User
from apps.backend.repositories import consent_repo
from apps.backend.services import consent_service
from shared.schemas.consent import ConsentSettings, ConsentUpdate, DataSourceInfo

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("", response_model=list[DataSourceInfo])
def get_consent(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return consent_service.get_catalog_with_state(db, user.id)


@router.post("", response_model=list[DataSourceInfo])
def set_consent_bulk(
    payload: ConsentSettings, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    for source, enabled in payload.model_dump().items():
        consent_service.set_consent(db, user.id, source, enabled)
    return consent_service.get_catalog_with_state(db, user.id)


@router.patch("/{source}", response_model=DataSourceInfo)
def patch_consent(
    source: str,
    payload: ConsentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    consent_service.set_consent(db, user.id, source, payload.enabled)
    return next(d for d in consent_service.get_catalog_with_state(db, user.id) if d.key == source)


@router.delete("/{source}", response_model=DataSourceInfo)
def delete_consent(source: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    consent_service.reset_consent(db, user.id, source)
    return next(d for d in consent_service.get_catalog_with_state(db, user.id) if d.key == source)


@router.get("/events")
def get_consent_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    events = consent_repo.list_consent_events(db, user.id)
    return [
        {
            "source": e.source,
            "action": e.action,
            "previous_value": e.previous_value,
            "new_value": e.new_value,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
