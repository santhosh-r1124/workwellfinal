from datetime import date as date_cls

from sqlalchemy.orm import Session

from apps.backend.core.observability import record_pattern_state
from apps.backend.core.timezones import today_in
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


def is_complete_day(day: date_cls, today: date_cls) -> bool:
    """A day the clock is still inside is not one you can compare.

    The agent reports every few minutes, so a row for today holds however
    much has happened so far. Set that beside a baseline built from whole
    days and every metric the morning has not produced yet reads as a
    collapse: "meetings -100%, focus -100%" at 09:00, every day, for
    everyone. The signal is not a drop - the day simply is not over.

    `today` is the employee's own today. Drawing it in UTC put someone in
    Auckland a full day behind and someone in Los Angeles a day ahead of
    their own evening.
    """
    return day < today


def employee_timezone(db: Session, employee_id: str) -> str:
    from apps.backend.models import User

    user = db.get(User, employee_id)
    return user.timezone if user else "UTC"


def usable_days(rows: list, timezone_name: str) -> list:
    """Days that are both measured and finished, in the employee's own
    reckoning of when a day ends."""
    today = today_in(timezone_name)
    return [
        d
        for d in rows
        if has_behavioral_data(telemetry_repo.daily_feature_to_dict(d))
        and is_complete_day(d.date, today)
    ]


def recompute_baselines(db: Session, employee_id: str) -> dict:
    all_history = telemetry_repo.daily_features_history(db, employee_id, limit_days=90)

    history = usable_days(all_history, employee_timezone(db, employee_id))
    history_dicts = [telemetry_repo.daily_feature_to_dict(d) for d in history]
    dates = [d.date for d in history]

    if not history_dicts:
        # No measured days yet. Writing a baseline here would store nine
        # rows of zeros that mean "we have no idea" but read as "this
        # person does no work" - and now that the daily sweep enqueues
        # every employee, it would do that for every new hire, every day.
        return {}

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
    return pattern


def get_baseline_response(db: Session, employee_id: str) -> dict:
    rows = baseline_repo.list_baselines(db, employee_id)

    # "Current" is the most recent day that actually has behavioral data
    # and is over - see has_behavioral_data and is_complete_day.
    recent = telemetry_repo.daily_features_history(db, employee_id, limit_days=14)
    measured = [
        telemetry_repo.daily_feature_to_dict(d)
        for d in usable_days(recent, employee_timezone(db, employee_id))
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
    as_of = current_dict.get("date")
    return {
        "employee_id": employee_id,
        # Which day these readings are from. The dashboard says so out
        # loud rather than implying "now".
        "as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else as_of,
        "metrics": metrics,
    }


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
