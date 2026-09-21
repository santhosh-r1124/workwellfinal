from sqlalchemy.orm import Session

from apps.backend.repositories import consent_repo
from shared.enums.data_sources import DEFAULT_ENABLED_SOURCES, DataSourceKey

BEHAVIORAL_SOURCES = [
    DataSourceKey.WORKING_HOURS,
    DataSourceKey.BREAK_PATTERNS,
    DataSourceKey.APPLICATION_CATEGORIES,
    DataSourceKey.TYPING_DYNAMICS,
]


def has_sufficient_consent(db: Session, employee_id: str) -> bool:
    """Gate for the orchestrator (Phase 6.1 'Consent Check'): at least one
    behavioral signal must be consented to before any analysis runs."""
    current = {c.source: c.enabled for c in consent_repo.list_consents(db, employee_id)}
    for source in BEHAVIORAL_SOURCES:
        if current.get(source.value, source in DEFAULT_ENABLED_SOURCES):
            return True
    return False
