from sqlalchemy.orm import Session

from apps.backend.core.observability import record_pattern_state
from apps.backend.repositories import baseline_repo, telemetry_repo
from ml.anomaly.pattern_builder import build_pattern_object
from ml.baseline.baseline_engine import compute_baseline
from ml.baseline.baseline_engine import deviation as baseline_deviation

TRACKED_METRICS = [
    "work_duration",
    "after_hours",
    "break_count",
    "average_break_gap",
    "meeting_hours",
    "context_switches",
    "focus_minutes",
    "typing_speed",
    "typing_pause_rate",
]


def has_behavioral_data(day: dict) -> bool:
    """A day with no recorded work is an absence of measurement, not an
    observation of zero.

    A daily-feature row gets created whenever anything touches the day -
    including a self-report submitted before any telemetry has arrived. Left
    in, those rows read as a day of zero work: they drag the baseline down
    and make the dashboard show every signal at -100%.
    """
    return (day.get("work_duration") or 0) > 0


def recompute_baselines(db: Session, employee_id: str) -> dict:
    all_history = telemetry_repo.daily_features_history(db, employee_id, limit_days=90)
    measured = [d for d in all_history if has_behavioral_data(telemetry_repo.daily_feature_to_dict(d))]

    history = measured
    history_dicts = [telemetry_repo.daily_feature_to_dict(d) for d in history]
    dates = [d.date for d in history]

    for metric in TRACKED_METRICS:
        values = [h.get(metric) for h in history_dicts]
        stats = compute_baseline(values, dates)
        baseline_repo.upsert_baseline(
            db,
            employee_id,
            metric,
            {
                "baseline_median": stats["median"],
                "baseline_mean": stats["mean"],
                "baseline_std": stats["std"],
                "baseline_mad": stats["mad"],
                "rolling_avg": stats["rolling_avg"],
                "trend": stats["trend"],
                "seasonality": stats["seasonality"],
                "window_days": stats["window_days"],
            },
        )

    pattern = None
    if history_dicts:
        pattern = build_pattern_object(employee_id, str(history_dicts[-1]["date"]), history_dicts)
        record_pattern_state(pattern["state"])
        baseline_repo.save_pattern_state(
            db,
            employee_id,
            history[-1].date,
            pattern["state"],
            pattern["confidence"],
            pattern["duration_days"],
            pattern["signals"],
        )
    return pattern or {}


def get_baseline_response(db: Session, employee_id: str) -> dict:
    rows = baseline_repo.list_baselines(db, employee_id)

    # "Current" is the most recent day that actually has behavioral data, not
    # simply the most recent row - see has_behavioral_data.
    recent = telemetry_repo.daily_features_history(db, employee_id, limit_days=14)
    measured = [
        telemetry_repo.daily_feature_to_dict(d)
        for d in recent
        if has_behavioral_data(telemetry_repo.daily_feature_to_dict(d))
    ]
    current_dict = measured[-1] if measured else {}

    metrics = {}
    for row in rows:
        stats = {"baseline": row.baseline_median, "median": row.baseline_median}
        current_value = current_dict.get(row.metric) or 0.0
        metrics[row.metric] = {
            "metric": row.metric,
            "baseline": row.baseline_median,
            "current": current_value,
            "deviation": baseline_deviation(current_value, stats),
            "median": row.baseline_median,
            "mean": row.baseline_mean,
            "std": row.baseline_std,
            "mad": row.baseline_mad,
            "rolling_avg": row.rolling_avg,
            "trend": row.trend,
            "window_days": row.window_days,
        }
    return {"employee_id": employee_id, "metrics": metrics}


def get_patterns(db: Session, employee_id: str) -> list[dict]:
    """One entry per day, newest state wins. Re-running the analysis writes a
    fresh row rather than updating in place, so without this the timeline
    shows the same day several times over."""
    rows = baseline_repo.recent_pattern_states(db, employee_id)

    by_date: dict[str, dict] = {}
    for r in rows:
        by_date[r.date.isoformat()] = {
            "id": r.id,
            "date": r.date.isoformat(),
            "state": r.state,
            "confidence": r.confidence,
            "duration_days": r.duration_days,
            "signals": r.signals,
        }
    return [by_date[key] for key in sorted(by_date)]
