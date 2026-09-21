def compute_recovery_features(events: list[dict]) -> dict:
    break_events = [e for e in events if (e.get("break_minutes") or 0) > 0]
    break_count = len(break_events)
    total_active = sum(e.get("active_minutes") or 0 for e in events)

    average_break_gap = round(total_active / break_count, 1) if break_count else round(total_active, 1)

    return {
        "break_count": break_count,
        "average_break_gap": average_break_gap,
    }
