from ml.aggregation.cohort import (
    ABSOLUTE_MIN_COHORT,
    aggregate_team_metrics,
    percentage_change,
)


def _windows(current: float, prior: float) -> dict:
    return {"current": [current] * 5, "prior": [prior] * 5}


def _team(size: int, current: float = 4.0, prior: float = 2.0) -> dict:
    return {f"emp{i}": {"meeting_hours": _windows(current, prior)} for i in range(size)}


def test_below_threshold_cohort_is_refused():
    result = aggregate_team_metrics(_team(3), ["meeting_hours"])
    assert result["sufficient_cohort"] is False
    assert result["metrics"] == {}
    assert "meeting_hours" in result["suppressed"]


def test_sufficient_cohort_reports_percentage_change():
    result = aggregate_team_metrics(_team(6), ["meeting_hours"])
    assert result["sufficient_cohort"] is True
    assert result["metrics"]["meeting_hours"]["change_pct"] == 100.0
    assert result["metrics"]["meeting_hours"]["direction"] == "up"


def test_admin_cannot_lower_threshold_below_absolute_floor():
    result = aggregate_team_metrics(_team(3), ["meeting_hours"], min_cohort=1)
    assert result["min_cohort"] == ABSOLUTE_MIN_COHORT
    assert result["sufficient_cohort"] is False


def test_configured_threshold_above_floor_is_respected():
    result = aggregate_team_metrics(_team(6), ["meeting_hours"], min_cohort=10)
    assert result["min_cohort"] == 10
    assert result["sufficient_cohort"] is False


def test_output_never_contains_employee_identifiers():
    team = _team(6)
    result = aggregate_team_metrics(team, ["meeting_hours"])
    serialized = str(result)
    for employee_id in team:
        assert employee_id not in serialized


def test_metric_suppressed_when_too_few_employees_have_both_windows():
    team = _team(6)
    # Only two employees have data in both windows for this metric.
    for i, (_, windows) in enumerate(team.items()):
        if i >= 2:
            windows["meeting_hours"]["prior"] = []
    result = aggregate_team_metrics(team, ["meeting_hours"])
    assert result["sufficient_cohort"] is True
    assert "meeting_hours" in result["suppressed"]
    assert "meeting_hours" not in result["metrics"]


def test_zero_prior_base_is_suppressed_not_reported_as_infinite():
    team = {f"emp{i}": {"after_hours": _windows(2.0, 0.0)} for i in range(6)}
    result = aggregate_team_metrics(team, ["after_hours"])
    assert "after_hours" in result["suppressed"]


def test_percentage_change_handles_zero_base():
    assert percentage_change(5.0, 0.0) is None
    assert percentage_change(3.0, 2.0) == 50.0
    assert percentage_change(1.0, 2.0) == -50.0
