def compute_communication_load(events: list[dict]) -> float:
    """Proxy for communication volume until Slack/email integrations (Phase 13)
    provide direct signal. Combines meeting time with app-switch volume."""
    meeting_minutes = sum(e.get("meeting_minutes") or 0 for e in events)
    switch_count = sum(e.get("application_switch_count") or 0 for e in events)
    return meeting_minutes + 0.5 * switch_count
