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
