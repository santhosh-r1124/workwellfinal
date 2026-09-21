"""Team-level aggregation (Phase 11).

The whole point of this module is what it refuses to emit. Individual
employees are never identifiable in the output: the only values that leave
here are percentage changes of a team-level median, and a metric is dropped
entirely unless enough distinct employees contributed data to *both* compared
windows. Callers get a per-metric `suppressed` list rather than a partial
number they might mistake for a full picture.
"""

import statistics

# Absolute floor, independent of any per-org configuration. An admin can
# raise the cohort threshold but can never lower it below this.
ABSOLUTE_MIN_COHORT = 5


def _median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def percentage_change(current: float, prior: float) -> float | None:
    """None when there is no meaningful base to compare against - reporting
    '+100%' off a zero base would overstate a change from nothing to almost
    nothing."""
    if prior == 0:
        return None
    return round((current - prior) / abs(prior) * 100, 1)


def aggregate_team_metrics(
    per_employee_windows: dict[str, dict[str, list[float]]],
    metrics: list[str],
    min_cohort: int = ABSOLUTE_MIN_COHORT,
) -> dict:
    """per_employee_windows maps employee_id -> {"current": [...], "prior": [...]}
    per metric, i.e. {employee_id: {metric: {"current": [..], "prior": [..]}}}.

    Returns only aggregate deltas plus the contributing cohort size. No
    employee identifier is ever part of the return value.
    """
    effective_min = max(min_cohort, ABSOLUTE_MIN_COHORT)

    cohort_size = len(per_employee_windows)
    if cohort_size < effective_min:
        return {
            "cohort_size": cohort_size,
            "min_cohort": effective_min,
            "sufficient_cohort": False,
            "metrics": {},
            "suppressed": list(metrics),
        }

    results: dict[str, dict] = {}
    suppressed: list[str] = []

    for metric in metrics:
        current_medians = []
        prior_medians = []

        for windows in per_employee_windows.values():
            metric_windows = windows.get(metric)
            if not metric_windows:
                continue
            current_values = metric_windows.get("current") or []
            prior_values = metric_windows.get("prior") or []
            # An employee only contributes to this metric if they have data
            # in both windows - otherwise the "change" is an artifact of who
            # happened to be present, not of the team's workload.
            if not current_values or not prior_values:
                continue
            current_medians.append(_median(current_values))
            prior_medians.append(_median(prior_values))

        if len(current_medians) < effective_min:
            suppressed.append(metric)
            continue

        current_team = _median(current_medians)
        prior_team = _median(prior_medians)
        change = percentage_change(current_team, prior_team)

        if change is None:
            suppressed.append(metric)
            continue

        results[metric] = {
            "change_pct": change,
            "direction": "up" if change > 0 else "down" if change < 0 else "flat",
            "contributing_employees": len(current_medians),
        }

    return {
        "cohort_size": cohort_size,
        "min_cohort": effective_min,
        "sufficient_cohort": True,
        "metrics": results,
        "suppressed": suppressed,
    }
