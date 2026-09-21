from ml.anomaly.persistence import consecutive_anomalous_days
from ml.anomaly.zscore import is_anomalous, robust_zscore
from ml.baseline.baseline_engine import compute_baseline
from shared.constants.wellbeing import (
    BASELINE_MIN_DAYS,
    NEVER_COLLECTED_LABELS,
    PERSISTENCE_MIN_DAYS,
    TRACKED_PATTERN_SIGNALS,
)
from shared.enums.pattern_states import PatternState


def build_pattern_object(employee_id: str, date_str: str, history: list[dict]) -> dict:
    """history: chronological list of merged daily+derived feature dicts
    (most recent last), each keyed by the field names in
    TRACKED_PATTERN_SIGNALS' values. Implements Phase 5.1-5.3: per-signal
    robust z-score anomaly detection, a persistence requirement before a
    signal counts, and assembly into the PatternObject the agent layer
    consumes.
    """
    signals = []
    max_duration = 0

    for name, field in TRACKED_PATTERN_SIGNALS.items():
        values = [d.get(field) for d in history if d.get(field) is not None]
        if len(values) < BASELINE_MIN_DAYS + 1:
            continue

        anomaly_flags = []
        for i in range(len(values)):
            if i < BASELINE_MIN_DAYS:
                anomaly_flags.append(False)
                continue
            baseline_stats = compute_baseline(values[:i])
            z = robust_zscore(values[i], baseline_stats)
            anomaly_flags.append(is_anomalous(z))

        duration = consecutive_anomalous_days(anomaly_flags)
        if duration == 0:
            continue

        baseline_stats = compute_baseline(values[:-1])
        baseline_value = baseline_stats.get("baseline", 0.0)
        current_value = values[-1]
        change = (
            round((current_value - baseline_value) / abs(baseline_value), 3)
            if baseline_value
            else round(current_value, 3)
        )
        signals.append({"name": name, "change": change, "anomalous_days": duration})
        max_duration = max(max_duration, duration)

    persistent = max_duration >= PERSISTENCE_MIN_DAYS
    state = PatternState.PATTERN_CHANGE if persistent else PatternState.STABLE
    confidence = round(min(0.99, 0.5 + 0.1 * len(signals) + 0.05 * max_duration), 2) if signals else 0.0

    return {
        "employee_id": employee_id,
        "date": date_str,
        "state": state.value,
        "confidence": confidence,
        "duration_days": max_duration,
        "signals": signals,
        "data_not_used": NEVER_COLLECTED_LABELS,
    }
