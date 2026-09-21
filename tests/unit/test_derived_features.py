from ml.features.derived_features import compute_derived_features


def _day(date, work_duration=8.0, after_hours=0.3, meeting_hours=1.5, break_count=4,
         average_break_gap=100.0, context_switches=30, focus_minutes=200.0):
    return {
        "date": date,
        "work_duration": work_duration,
        "after_hours": after_hours,
        "meeting_hours": meeting_hours,
        "break_count": break_count,
        "average_break_gap": average_break_gap,
        "context_switches": context_switches,
        "focus_minutes": focus_minutes,
        "typing_speed": 50,
        "self_report_stress": None,
        "self_report_energy": None,
        "self_report_recovery": None,
    }


def test_derived_features_empty_history():
    assert compute_derived_features([]) == {}


def test_overtime_frequency_counts_days_over_threshold():
    history = [_day(f"2026-01-{i:02d}", work_duration=10.0) for i in range(1, 8)]
    derived = compute_derived_features(history)
    assert derived["overtime_frequency"] == 1.0


def test_meeting_load_ratio():
    history = [_day("2026-01-01", work_duration=8.0, meeting_hours=4.0)]
    derived = compute_derived_features(history)
    assert derived["meeting_load"] == 0.5


def test_context_switch_rate_scales_by_work_duration():
    history = [_day("2026-01-01", work_duration=5.0, context_switches=50)]
    derived = compute_derived_features(history)
    assert derived["context_switch_rate"] == 10.0
