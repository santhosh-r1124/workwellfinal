from shared.constants.wellbeing import PERSISTENCE_MIN_DAYS


def consecutive_anomalous_days(anomaly_flags: list[bool]) -> int:
    """Count the current run of anomalous days ending at the most recent day.
    A single normal day resets the run (Phase 5.2)."""
    count = 0
    for flag in reversed(anomaly_flags):
        if flag:
            count += 1
        else:
            break
    return count


def is_persistent_pattern(anomaly_flags: list[bool], min_days: int = PERSISTENCE_MIN_DAYS) -> bool:
    return consecutive_anomalous_days(anomaly_flags) >= min_days
