from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import DailyFeature, OrgSettings, User
from ml.aggregation.cohort import ABSOLUTE_MIN_COHORT, aggregate_team_metrics

WINDOW_DAYS = 14

# Team-level metrics deliberately mirror the employee dashboard's neutral
# vocabulary - workload/recovery/focus/schedule - never a wellness score.
TEAM_METRICS = [
    "meeting_hours",
    "after_hours",
    "focus_minutes",
    "average_break_gap",
    "work_duration",
    "context_switches",
]

METRIC_LABELS = {
    "meeting_hours": "Meeting load",
    "after_hours": "After-hours work",
    "focus_minutes": "Focus time",
    "average_break_gap": "Recovery gaps",
    "work_duration": "Work duration",
    "context_switches": "Context switching",
}


def get_min_cohort(db: Session, org_id: str) -> int:
    settings = db.scalar(select(OrgSettings).where(OrgSettings.org_id == org_id))
    configured = settings.aggregation_min_cohort if settings else ABSOLUTE_MIN_COHORT
    return max(configured, ABSOLUTE_MIN_COHORT)


def list_teams(db: Session, org_id: str) -> list[str]:
    rows = db.scalars(
        select(User.team).where(User.org_id == org_id, User.team.isnot(None)).distinct()
    )
    return sorted({r for r in rows if r})


def team_analytics(db: Session, org_id: str, team: str, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    current_start = as_of - timedelta(days=WINDOW_DAYS)
    prior_start = as_of - timedelta(days=WINDOW_DAYS * 2)

    member_ids = list(
        db.scalars(select(User.id).where(User.org_id == org_id, User.team == team))
    )

    per_employee: dict[str, dict[str, dict[str, list[float]]]] = {}

    if member_ids:
        rows = db.scalars(
            select(DailyFeature).where(
                DailyFeature.employee_id.in_(member_ids),
                DailyFeature.date > prior_start,
                DailyFeature.date <= as_of,
            )
        )
        for row in rows:
            window = "current" if row.date > current_start else "prior"
            employee_windows = per_employee.setdefault(row.employee_id, {})
            for metric in TEAM_METRICS:
                value = getattr(row, metric, None)
                if value is None:
                    continue
                metric_windows = employee_windows.setdefault(metric, {"current": [], "prior": []})
                metric_windows[window].append(float(value))

    aggregate = aggregate_team_metrics(
        per_employee, TEAM_METRICS, min_cohort=get_min_cohort(db, org_id)
    )

    return {
        "team": team,
        "window_days": WINDOW_DAYS,
        "as_of": as_of.isoformat(),
        "labels": METRIC_LABELS,
        **aggregate,
    }
