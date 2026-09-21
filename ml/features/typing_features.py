def compute_typing_features(events: list[dict]) -> dict:
    speeds = [e["typing_speed"] for e in events if e.get("typing_speed") is not None]
    pauses = [e["pause_rate"] for e in events if e.get("pause_rate") is not None]

    return {
        "typing_speed": round(sum(speeds) / len(speeds), 1) if speeds else 0.0,
        "typing_pause_rate": round(sum(pauses) / len(pauses), 3) if pauses else 0.0,
    }
