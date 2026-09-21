from datetime import time

AFTER_HOURS_START = time(18, 0)
AFTER_HOURS_END = time(7, 0)


def compute_schedule_features(events: list[dict]) -> dict:
    """events: list of {"timestamp": datetime, "active_minutes": float, ...}"""
    active_minutes = sum(e.get("active_minutes") or 0 for e in events)

    after_hours_minutes = 0.0
    for e in events:
        ts = e.get("timestamp")
        if ts is None:
            continue
        t = ts.time()
        if t >= AFTER_HOURS_START or t < AFTER_HOURS_END:
            after_hours_minutes += e.get("active_minutes") or 0

    return {
        "work_duration": round(active_minutes / 60, 2),
        "after_hours": round(after_hours_minutes / 60, 2),
    }
