from agents.providers.base import AIProvider
from shared.enums.intervention import InterventionType
from shared.enums.pattern_states import PatternState

SYSTEM_PROMPT = (
    "You are the Intervention Agent for WorkWell AI. Write a short (1-2 sentence), "
    "supportive, non-alarming message proposing the given intervention to the employee. "
    "Use a suggestion tone ('you might consider'), never a directive or clinical tone."
)

# Maps the dominant strain component to the least-intrusive matching nudge
# (Phase 6.5). Order matters: checked most-specific-cause first.
COMPONENT_TO_INTERVENTION = {
    "meeting_pressure": InterventionType.FOCUS_BLOCK,
    "schedule_strain": InterventionType.SHUTDOWN_REMINDER,
    "recovery_strain": InterventionType.RECOVERY_BREAK,
    "focus_fragmentation": InterventionType.FOCUS_BLOCK,
}

INTERVENTION_RATIONALE = {
    InterventionType.FOCUS_BLOCK: "Meeting load and context switching are elevated; a protected focus block is a low-friction way to recover uninterrupted work time.",
    InterventionType.SHUTDOWN_REMINDER: "After-hours activity is elevated; a shutdown reminder nudges a boundary without requiring a workload change.",
    InterventionType.RECOVERY_BREAK: "Break frequency has dropped below this employee's own norm; a recovery reminder addresses that directly.",
    InterventionType.WORKPLACE_SUPPORT_OFFER: "The strain pattern is sustained and elevated across multiple signals; offering workplace support resources is the appropriate next step.",
    InterventionType.NO_ACTION: "No sustained deviation from baseline was detected.",
}


def propose_intervention(risk: dict, provider: AIProvider) -> dict:
    state = risk.get("state", PatternState.STABLE.value)
    scores = risk.get("component_scores", {})

    if state in (PatternState.SUSTAINED_STRAIN.value, PatternState.SUPPORT_RECOMMENDED.value):
        intervention_type = InterventionType.WORKPLACE_SUPPORT_OFFER
    elif state == PatternState.PATTERN_CHANGE.value and scores:
        dominant = max(scores, key=lambda k: scores.get(k, 0.0))
        intervention_type = COMPONENT_TO_INTERVENTION.get(dominant, InterventionType.NO_ACTION)
    else:
        intervention_type = InterventionType.NO_ACTION

    rationale = INTERVENTION_RATIONALE[intervention_type]

    if intervention_type == InterventionType.NO_ACTION:
        message = ""
    else:
        prompt = f"Intervention type: {intervention_type.value}. Reason: {rationale}"
        message = provider.generate(prompt, system=SYSTEM_PROMPT)

    return {"type": intervention_type.value, "message": message, "rationale": rationale}
