from shared.enums.pattern_states import PatternState

# Weighted fusion of component strain scores (each already normalized 0..1
# upstream). Deterministic and rule-based by design (Phase 6.4): the LLM
# explains this output, it never computes or overrides it.
COMPONENT_WEIGHTS = {
    "schedule_strain": 0.2,
    "recovery_strain": 0.25,
    "meeting_pressure": 0.2,
    "focus_fragmentation": 0.15,
    "typing_deviation": 0.05,
    "self_report": 0.15,
}

SUSTAINED_STRAIN_THRESHOLD = 0.6
SUPPORT_RECOMMENDED_THRESHOLD = 0.75


def compute_component_scores(pattern_signals: list[dict]) -> dict:
    """Map named pattern-detection signals (Phase 5.3) onto the fixed set of
    risk components, scaling each signal's fractional change into a 0..1
    strain score."""
    by_name = {s["name"]: s for s in pattern_signals}

    def score_for(signal_name: str, scale: float = 1.0) -> float:
        signal = by_name.get(signal_name)
        if not signal:
            return 0.0
        return round(max(0.0, min(1.0, abs(signal["change"]) * scale)), 3)

    return {
        "schedule_strain": score_for("after_hours_work", scale=1.5),
        "recovery_strain": score_for("recovery_gap", scale=1.0),
        "meeting_pressure": score_for("meeting_load", scale=1.2),
        "focus_fragmentation": score_for("focus_fragmentation", scale=1.0),
        "typing_deviation": score_for("typing_deviation", scale=1.0),
        "self_report": 0.0,  # filled in by fuse_risk when self-report data is available
    }


def fuse_risk(
    component_scores: dict,
    persistent_pattern: bool,
    self_report_strain: float = 0.0,
    safety_flag: bool = False,
) -> dict:
    scores = {**component_scores, "self_report": self_report_strain}
    overall = round(sum(scores.get(k, 0.0) * w for k, w in COMPONENT_WEIGHTS.items()), 3)

    if safety_flag:
        state = PatternState.SAFETY_EVENT
    elif persistent_pattern and overall >= SUPPORT_RECOMMENDED_THRESHOLD:
        state = PatternState.SUPPORT_RECOMMENDED
    elif persistent_pattern and overall >= SUSTAINED_STRAIN_THRESHOLD:
        state = PatternState.SUSTAINED_STRAIN
    elif persistent_pattern:
        state = PatternState.PATTERN_CHANGE
    else:
        state = PatternState.STABLE

    return {
        "state": state.value,
        "component_scores": scores,
        "overall_score": overall,
    }
