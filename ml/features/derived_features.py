from datetime import date as date_type

OVERTIME_THRESHOLD_HOURS = 9.0
AFTER_HOURS_THRESHOLD = 1.0
FREQUENCY_WINDOW_DAYS = 14
GROWTH_WINDOW_DAYS = 7


def _rate(items: list[bool]) -> float:
    return round(sum(1 for x in items if x) / len(items), 3) if items else 0.0


def _avg(values: list[float]) -> float:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def _growth(current: float, prior_avg: float) -> float:
    if prior_avg == 0:
        return 0.0 if current == 0 else 1.0
    return round((current - prior_avg) / prior_avg, 3)


def compute_derived_features(history: list[dict], baseline: dict | None = None) -> dict:
    """history: chronological list of daily_feature dicts (Phase 3.1 shape),
    most recent last. baseline: optional dict of metric -> baseline stats
    (median) from ml.baseline.baseline_engine, used for recovery_gap and
    typing_deviation which are meaningful only relative to the employee's
    own norm."""
    if not history:
        return {}

    current = history[-1]
    window = history[-FREQUENCY_WINDOW_DAYS:]
    recent = history[-GROWTH_WINDOW_DAYS:]
    prior = history[-2 * GROWTH_WINDOW_DAYS : -GROWTH_WINDOW_DAYS] or recent

    overtime_frequency = _rate([d.get("work_duration", 0) > OVERTIME_THRESHOLD_HOURS for d in window])
    after_hours_frequency = _rate([d.get("after_hours", 0) > AFTER_HOURS_THRESHOLD for d in window])

    weekend_days = [d for d in window if _is_weekend(d.get("date"))]
    weekend_work_frequency = _rate([d.get("work_duration", 0) > 0 for d in weekend_days])

    work_duration = current.get("work_duration", 0) or 0
    meeting_hours = current.get("meeting_hours", 0) or 0
    meeting_load = round(meeting_hours / work_duration, 3) if work_duration else 0.0
    meeting_growth = _growth(meeting_hours, _avg([d.get("meeting_hours") for d in prior]))

    baseline = baseline or {}
    break_baseline = baseline.get("break_count", {}).get("baseline") if baseline.get("break_count") else None
    break_debt = max(0.0, (break_baseline or _avg([d.get("break_count") for d in prior])) - current.get("break_count", 0))

    gap_baseline = (
        baseline.get("average_break_gap", {}).get("baseline")
        if baseline.get("average_break_gap")
        else _avg([d.get("average_break_gap") for d in prior])
    )
    recovery_gap = round(current.get("average_break_gap", 0) - gap_baseline, 1)

    context_switch_rate = round(current.get("context_switches", 0) / work_duration, 1) if work_duration else 0.0
    focus_fragmentation = (
        round(1 - (current.get("focus_minutes", 0) / (work_duration * 60)), 3) if work_duration else 0.0
    )
    focus_fragmentation = max(0.0, min(1.0, focus_fragmentation))

    typing_baseline = (
        baseline.get("typing_speed", {}).get("baseline")
        if baseline.get("typing_speed")
        else _avg([d.get("typing_speed") for d in prior])
    )
    typing_deviation = _growth(current.get("typing_speed", 0), typing_baseline) if typing_baseline else 0.0

    communication_pressure = round(min(1.0, meeting_load * 0.6 + min(context_switch_rate / 20, 1) * 0.4), 3)

    workload_growth = _growth(work_duration, _avg([d.get("work_duration") for d in prior]))

    self_report_trend = _self_report_trend(recent)

    return {
        "overtime_frequency": overtime_frequency,
        "after_hours_frequency": after_hours_frequency,
        "weekend_work_frequency": weekend_work_frequency,
        "meeting_load": meeting_load,
        "meeting_growth": meeting_growth,
        "break_debt": round(break_debt, 1),
        "recovery_gap": recovery_gap,
        "context_switch_rate": context_switch_rate,
        "focus_fragmentation": focus_fragmentation,
        "typing_deviation": typing_deviation,
        "communication_pressure": communication_pressure,
        "workload_growth": workload_growth,
        "self_report_trend": self_report_trend,
    }


def _is_weekend(date_value) -> bool:
    if date_value is None:
        return False
    if isinstance(date_value, str):
        date_value = date_type.fromisoformat(date_value)
    return date_value.weekday() >= 5


def _self_report_trend(recent: list[dict]) -> float:
    stress = [d.get("self_report_stress") for d in recent if d.get("self_report_stress") is not None]
    energy = [d.get("self_report_energy") for d in recent if d.get("self_report_energy") is not None]
    recovery = [d.get("self_report_recovery") for d in recent if d.get("self_report_recovery") is not None]

    if not stress and not energy and not recovery:
        return 0.0

    def slope(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den else 0.0

    # Rising stress + falling energy/recovery = increasing strain (positive value)
    return round(slope(stress) - slope(energy) - slope(recovery), 3)
