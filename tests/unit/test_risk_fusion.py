from ml.risk.risk_fusion import compute_component_scores, fuse_risk
from shared.enums.pattern_states import PatternState


def test_no_persistence_is_stable():
    result = fuse_risk({"schedule_strain": 0.9}, persistent_pattern=False)
    assert result["state"] == PatternState.STABLE.value


def test_persistent_low_score_is_pattern_change():
    scores = {"recovery_strain": 0.1}
    result = fuse_risk(scores, persistent_pattern=True)
    assert result["state"] == PatternState.PATTERN_CHANGE.value


def test_persistent_high_score_is_support_recommended():
    scores = {
        "schedule_strain": 1.0,
        "recovery_strain": 1.0,
        "meeting_pressure": 1.0,
        "focus_fragmentation": 1.0,
        "typing_deviation": 1.0,
    }
    result = fuse_risk(scores, persistent_pattern=True, self_report_strain=1.0)
    assert result["state"] == PatternState.SUPPORT_RECOMMENDED.value
    assert result["overall_score"] == 1.0


def test_safety_flag_overrides_everything():
    result = fuse_risk({}, persistent_pattern=False, safety_flag=True)
    assert result["state"] == PatternState.SAFETY_EVENT.value


def test_compute_component_scores_maps_named_signals():
    signals = [{"name": "meeting_load", "change": 0.5, "anomalous_days": 6}]
    scores = compute_component_scores(signals)
    assert scores["meeting_pressure"] == 0.6
    assert scores["schedule_strain"] == 0.0
