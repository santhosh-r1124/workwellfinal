from datetime import date, datetime

from sqlalchemy.orm import Session

from apps.backend.repositories import consent_repo, telemetry_repo
from ml.features.daily_vector import build_daily_feature_vector
from ml.features.derived_features import compute_derived_features
from shared.constants.data_sources import FIELD_GATES
from shared.enums.data_sources import DEFAULT_ENABLED_SOURCES, DataSourceKey


def _consent_map(db: Session, employee_id: str) -> dict[str, bool]:
    current = {c.source: c.enabled for c in consent_repo.list_consents(db, employee_id)}
    return {
        src.value: current.get(src.value, src in DEFAULT_ENABLED_SOURCES) for src in DataSourceKey
    }


def filter_features_by_consent(db: Session, employee_id: str, features: dict) -> dict:
    consents = _consent_map(db, employee_id)
    filtered = dict(features)
    for source, fields in FIELD_GATES.items():
        if not consents.get(source.value, False):
            for field in fields:
                filtered.pop(field, None)
    return filtered


def ingest_event(db: Session, employee_id: str, timestamp: datetime, features: dict):
    clean = filter_features_by_consent(db, employee_id, features)
    return telemetry_repo.create_event(db, employee_id, timestamp, clean)


def recompute_daily_feature(db: Session, employee_id: str, day: date):
    events = telemetry_repo.events_for_day(db, employee_id, day)
    event_dicts = [{"timestamp": e.timestamp, **e.features} for e in events]

    self_report = telemetry_repo.self_report_for_day(db, employee_id, day)
    self_report_dict = (
        {"stress": self_report.stress, "energy": self_report.energy, "recovery": self_report.recovery}
        if self_report
        else None
    )

    vector = build_daily_feature_vector(employee_id, day.isoformat(), event_dicts, self_report_dict)

    history = telemetry_repo.daily_features_history(db, employee_id, limit_days=59)
    history_dicts = [telemetry_repo.daily_feature_to_dict(d) for d in history if d.date != day]
    history_dicts.append({**vector, "date": day})

    derived = compute_derived_features(history_dicts)
    vector["derived"] = derived

    values = {k: v for k, v in vector.items() if k not in ("employee_id", "date")}
    return telemetry_repo.upsert_daily_feature(db, employee_id, day, values)
