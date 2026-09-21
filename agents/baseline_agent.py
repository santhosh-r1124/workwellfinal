from agents.providers.base import AIProvider

SYSTEM_PROMPT = (
    "You are the Baseline Agent for WorkWell AI. You are given precomputed statistical "
    "deviations for one employee's work-pattern metrics versus their own historical baseline. "
    "Explain in plain, neutral language what changed and by how much. Never invent numbers "
    "that are not in the input. Never diagnose a mental health condition. Keep it to 2-3 "
    "sentences."
)


def explain_baseline(baseline_response: dict, provider: AIProvider) -> dict:
    metrics = baseline_response.get("metrics", {})
    changes = [
        {"metric": name, "baseline": m["baseline"], "current": m["current"], "deviation": m["deviation"]}
        for name, m in metrics.items()
        if abs(m.get("deviation", 0)) > 0
    ]
    changes.sort(key=lambda c: abs(c["deviation"]), reverse=True)

    if not changes:
        return {"changes": [], "confidence": 0.0, "explanation": "No meaningful deviation from baseline."}

    confidence = min(0.95, 0.4 + 0.1 * len(changes))
    prompt = "Deviations from personal baseline:\n" + "\n".join(
        f"- {c['metric']}: baseline={c['baseline']}, current={c['current']}, deviation={c['deviation']:+}"
        for c in changes[:6]
    )
    explanation = provider.generate(prompt, system=SYSTEM_PROMPT)

    return {"changes": changes, "confidence": round(confidence, 2), "explanation": explanation}
