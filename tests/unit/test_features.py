from datetime import datetime

from ml.features.daily_vector import build_daily_feature_vector
from ml.features.focus_features import compute_focus_features
from ml.features.meeting_features import compute_meeting_features
from ml.features.recovery_features import compute_recovery_features
from ml.features.schedule_features import compute_schedule_features
from ml.features.typing_features import compute_typing_features


def test_schedule_features_splits_after_hours():
    events = [
        {"timestamp": datetime(2026, 1, 5, 10, 0), "active_minutes": 120},
        {"timestamp": datetime(2026, 1, 5, 19, 30), "active_minutes": 60},
    ]
    result = compute_schedule_features(events)
    assert result["work_duration"] == 3.0
    assert result["after_hours"] == 1.0


def test_recovery_features_break_count_and_gap():
    events = [
        {"active_minutes": 100},
        {"break_minutes": 15, "active_minutes": 0},
        {"active_minutes": 100},
        {"break_minutes": 15, "active_minutes": 0},
    ]
    result = compute_recovery_features(events)
    assert result["break_count"] == 2
    assert result["average_break_gap"] == 100.0


def test_meeting_features():
    events = [{"meeting_minutes": 30}, {"meeting_minutes": 45}]
    assert compute_meeting_features(events) == {"meeting_hours": 1.25}


def test_focus_features():
    events = [
        {"context_switches": 5, "continuous_session_minutes": 20},
        {"context_switches": 7, "continuous_session_minutes": 15},
    ]
    result = compute_focus_features(events)
    assert result["context_switches"] == 12
    assert result["focus_minutes"] == 35.0


def test_typing_features_ignores_missing_values():
    events = [{"typing_speed": 50, "pause_rate": 0.1}, {"typing_speed": None, "pause_rate": 0.2}]
    result = compute_typing_features(events)
    assert result["typing_speed"] == 50.0
    assert result["typing_pause_rate"] == 0.15


def test_build_daily_feature_vector_merges_self_report():
    events = [{"timestamp": datetime(2026, 1, 5, 10, 0), "active_minutes": 60}]
    vector = build_daily_feature_vector(
        "emp1", "2026-01-05", events, self_report={"stress": 3, "energy": 4, "recovery": 4}
    )
    assert vector["employee_id"] == "emp1"
    assert vector["self_report_stress"] == 3
    assert vector["work_duration"] == 1.0


def test_build_daily_feature_vector_without_self_report():
    vector = build_daily_feature_vector("emp1", "2026-01-05", [], self_report=None)
    assert vector["self_report_stress"] is None
