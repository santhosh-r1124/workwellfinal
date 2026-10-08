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


WELLBEING_METRICS = {
    "stress": "Self-reported stress",
    "energy": "Self-reported energy",
    "recovery": "Self-reported recovery",
}


def wellness_overview(db: Session, org_id: str, as_of: date | None = None) -> dict:
    """Organisation-wide wellbeing view for the wellness team.

    Same rule as team analytics: only aggregates, and nothing at all unless
    the cohort floor is met. Check-in scores are compared as a median of
    per-person medians (current vs prior window); pattern states are
    reported as counts, never as names.
    """
    from apps.backend.models import Role, SelfReport
    from apps.backend.repositories import baseline_repo
    from shared.enums.roles import RoleName

    as_of = as_of or date.today()
    current_start = as_of - timedelta(days=WINDOW_DAYS)
    prior_start = as_of - timedelta(days=WINDOW_DAYS * 2)
    min_cohort = get_min_cohort(db, org_id)

    employee_ids = list(
        db.scalars(
            select(User.id)
            .join(Role, Role.id == User.role_id)
            .where(
                User.org_id == org_id,
                User.is_active.is_(True),
                Role.name == RoleName.EMPLOYEE.value,
            )
        )
    )

    per_employee: dict[str, dict[str, dict[str, list[float]]]] = {}
    weekly: dict[int, dict[str, dict[str, list[float]]]] = {}
    if employee_ids:
        reports = db.scalars(
            select(SelfReport).where(
                SelfReport.employee_id.in_(employee_ids),
                SelfReport.date > prior_start,
                SelfReport.date <= as_of,
            )
        )
        for r in reports:
            window = "current" if r.date > current_start else "prior"
            week = (as_of - r.date).days // 7
            for metric in WELLBEING_METRICS:
                value = float(getattr(r, metric))
                per_employee.setdefault(r.employee_id, {}).setdefault(
                    metric, {"current": [], "prior": []}
                )[window].append(value)
                weekly.setdefault(week, {}).setdefault(r.employee_id, {}).setdefault(
                    metric, []
                ).append(value)

    aggregate = aggregate_team_metrics(per_employee, list(WELLBEING_METRICS), min_cohort=min_cohort)
    sufficient = aggregate["sufficient_cohort"]

    import statistics

    trend = []
    if sufficient:
        for week in sorted(weekly, reverse=True):
            people = weekly[week]
            if len(people) < min_cohort:
                continue
            point = {"week_ending": (as_of - timedelta(days=7 * week)).isoformat(), "contributors": len(people)}
            for metric in WELLBEING_METRICS:
                medians = [statistics.median(v[metric]) for v in people.values() if v.get(metric)]
                point[metric] = round(float(statistics.median(medians)), 2) if medians else None
            trend.append(point)

    states: dict[str, int] = {}
    for employee_id in employee_ids:
        latest = baseline_repo.recent_pattern_states(db, employee_id, limit=1)
        state = latest[-1].state if latest else "BASELINE_BUILDING"
        states[state] = states.get(state, 0) + 1

    return {
        "as_of": as_of.isoformat(),
        "window_days": WINDOW_DAYS,
        "labels": WELLBEING_METRICS,
        "scale_max": 5,
        "employees": len(employee_ids),
        "pattern_states": states if len(employee_ids) >= min_cohort else {},
        "trend": trend,
        **aggregate,
    }
