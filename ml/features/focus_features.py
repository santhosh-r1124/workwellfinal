def compute_focus_features(events: list[dict]) -> dict:
    context_switches = sum(e.get("context_switches") or 0 for e in events)
    focus_minutes = sum(e.get("continuous_session_minutes") or 0 for e in events)
    return {
        "context_switches": int(context_switches),
        "focus_minutes": round(focus_minutes, 1),
    }
