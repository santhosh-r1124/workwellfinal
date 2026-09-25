from sqlalchemy.orm import Session

from apps.backend.services import telemetry_service
from shared.enums.data_sources import DataSourceKey

BEHAVIORAL_SOURCES = [
    DataSourceKey.WORKING_HOURS,
    DataSourceKey.BREAK_PATTERNS,
    DataSourceKey.APPLICATION_CATEGORIES,
    DataSourceKey.TYPING_DYNAMICS,
]


def has_sufficient_consent(db: Session, employee_id: str) -> bool:
    """Gate for the orchestrator (Phase 6.1 'Consent Check'): at least one
    behavioral signal must be consented to before any analysis runs."""
    consents = telemetry_service.consent_map(db, employee_id)
    return any(consents.get(source.value, False) for source in BEHAVIORAL_SOURCES)
