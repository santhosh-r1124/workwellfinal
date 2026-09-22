from ml.anomaly.pattern_builder import build_pattern_object
from shared.enums.pattern_states import PatternState


def _stable_history(days: int = 20) -> list[dict]:
    return [
        {
            "date": f"2026-01-{i + 1:02d}",
            "after_hours": 0.3,
            "meeting_load": 0.2,
            "recovery_gap": 0.0,
            "context_switch_rate": 3.0,
            "focus_fragmentation": 0.4,
            "typing_deviation": 0.0,
        }
        for i in range(days)
    ]


def test_stable_history_produces_stable_state():
    result = build_pattern_object("emp1", "2026-01-20", _stable_history())
    assert result["state"] == PatternState.STABLE.value
    assert result["duration_days"] == 0


def test_sustained_shift_produces_pattern_change():
    history = _stable_history(15)
    for i in range(10):
        history.append(
            {
                "date": f"2026-02-{i + 1:02d}",
                "after_hours": 3.5,
                "meeting_load": 0.2,
                "recovery_gap": 0.0,
                "context_switch_rate": 3.0,
                "focus_fragmentation": 0.4,
                "typing_deviation": 0.0,
            }
        )
    result = build_pattern_object("emp1", "2026-02-10", history)
    assert result["state"] == PatternState.PATTERN_CHANGE.value
    assert result["duration_days"] >= 5
    assert any(s["name"] == "after_hours_work" for s in result["signals"])


def test_data_not_used_is_always_present():
    result = build_pattern_object("emp1", "2026-01-20", _stable_history())
    assert "Webcam" in result["data_not_used"]
    assert "Raw keyboard" in result["data_not_used"]


def test_change_does_not_explode_for_signals_centred_near_zero():
    """recovery_gap and typing_deviation are differences centred near zero.
    Dividing by that centre produced "+4467%" in the employee-facing
    explanation; the denominator is floored at the signal's own spread."""
    history = []
    for i in range(15):
        history.append(
            {
                "date": f"2026-01-{i + 1:02d}",
                "after_hours": 0.3,
                "meeting_load": 0.2,
                "recovery_gap": 0.01 if i % 2 else -0.01,  # centred on ~0
                "context_switch_rate": 3.0,
                "focus_fragmentation": 0.4,
                "typing_deviation": 0.0,
            }
        )
    for i in range(10):
        history.append(
            {
                "date": f"2026-02-{i + 1:02d}",
                "after_hours": 0.3,
                "meeting_load": 0.2,
                "recovery_gap": 2.5,
                "context_switch_rate": 3.0,
                "focus_fragmentation": 0.4,
                "typing_deviation": 0.0,
            }
        )

    result = build_pattern_object("emp1", "2026-02-10", history)
    recovery = next(s for s in result["signals"] if s["name"] == "recovery_gap")

    # Still detected, but reported in units of typical variation rather than
    # as a percentage of a near-zero centre.
    assert recovery["anomalous_days"] >= 5
    assert recovery["change_kind"] == "spread"


def test_ordinary_signals_still_report_a_percentage():
    history = _stable_history(15)
    for i in range(10):
        history.append(
            {
                "date": f"2026-02-{i + 1:02d}",
                "after_hours": 3.5,
                "meeting_load": 0.2,
                "recovery_gap": 0.0,
                "context_switch_rate": 3.0,
                "focus_fragmentation": 0.4,
                "typing_deviation": 0.0,
            }
        )
    result = build_pattern_object("emp1", "2026-02-10", history)
    after_hours = next(s for s in result["signals"] if s["name"] == "after_hours_work")

    assert after_hours["change_kind"] == "relative"
    # baseline 0.3 -> 3.5 is a ~10x rise, reported as a plain ratio.
    assert 9 < after_hours["change"] < 12
