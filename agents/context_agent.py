from agents.providers.base import AIProvider

SYSTEM_PROMPT = (
    "You are the Context Agent for WorkWell AI. You are given a list of candidate workplace "
    "contexts that could plausibly explain a detected work-pattern change (e.g. a release "
    "period, a meeting increase), along with an optional short note the employee wrote "
    "themselves. Write one or two cautious sentences using language like 'may explain' or "
    "'could account for'. Never assert a diagnosis or a certain cause. Never mention anxiety, "
    "depression, or any clinical condition."
)

# Rule-based hypothesis generation: the agent frames plausible workplace
# explanations, it does not get to invent them from nothing (Phase 6.3).
SIGNAL_TO_CONTEXT = {
    "meeting_load": "meeting_increase",
    "after_hours_work": "release_period",
    "context_switch_rate": "cross_team_coordination",
    "focus_fragmentation": "cross_team_coordination",
    "recovery_gap": "sustained_workload",
    "typing_deviation": "fatigue_or_tooling_change",
}


def analyze_context(pattern: dict, employee_note: str | None = None) -> dict:
    from agents.providers import get_provider

    provider: AIProvider = get_provider()

    signal_names = {s["name"] for s in pattern.get("signals", [])}
    likely_context = sorted({SIGNAL_TO_CONTEXT[n] for n in signal_names if n in SIGNAL_TO_CONTEXT})

    if not likely_context:
        return {"likely_context": [], "context_confidence": 0.0, "explanation": "No pattern change to contextualize."}

    context_confidence = round(min(0.9, 0.5 + 0.1 * len(likely_context)), 2)

    prompt = (
        f"Candidate contexts: {', '.join(likely_context)}.\n"
        f"Employee note: {employee_note or '(none provided)'}"
    )
    explanation = provider.generate(prompt, system=SYSTEM_PROMPT)

    return {
        "likely_context": likely_context,
        "context_confidence": context_confidence,
        "explanation": explanation,
    }
