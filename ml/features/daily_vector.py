from ml.features.focus_features import compute_focus_features
from ml.features.meeting_features import compute_meeting_features
from ml.features.recovery_features import compute_recovery_features
from ml.features.schedule_features import compute_schedule_features
from ml.features.typing_features import compute_typing_features


def build_daily_feature_vector(
    employee_id: str,
    date_str: str,
    events: list[dict],
    self_report: dict | None = None,
) -> dict:
    """Combine raw telemetry events for one employee/day into the Phase 3.1
    daily feature vector."""
    vector = {"employee_id": employee_id, "date": date_str}
    vector.update(compute_schedule_features(events))
    vector.update(compute_recovery_features(events))
    vector.update(compute_meeting_features(events))
    vector.update(compute_focus_features(events))
    vector.update(compute_typing_features(events))

    if self_report:
        vector["self_report_stress"] = self_report.get("stress")
        vector["self_report_energy"] = self_report.get("energy")
        vector["self_report_recovery"] = self_report.get("recovery")
    else:
        vector["self_report_stress"] = None
        vector["self_report_energy"] = None
        vector["self_report_recovery"] = None

    return vector
