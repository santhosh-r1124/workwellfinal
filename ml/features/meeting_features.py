def compute_meeting_features(events: list[dict]) -> dict:
    meeting_minutes = sum(e.get("meeting_minutes") or 0 for e in events)
    return {"meeting_hours": round(meeting_minutes / 60, 2)}
