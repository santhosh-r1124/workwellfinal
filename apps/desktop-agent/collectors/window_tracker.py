from collectors.window_collector import get_active_window_title, is_meeting_window


class WindowTracker:
    """Polled (not event-driven) since there is no cross-platform foreground
    window change notification. Only ever stores the current title in
    memory to detect a change; nothing is written to disk."""

    def __init__(self, poll_interval_seconds: float = 30.0) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._last_title: str | None = None
        self._switch_count = 0
        self._meeting_seconds = 0.0

    def poll_once(self) -> None:
        title = get_active_window_title()
        if title != self._last_title:
            self._switch_count += 1
            self._last_title = title
        if is_meeting_window(title):
            self._meeting_seconds += self.poll_interval_seconds

    def drain_window(self) -> dict:
        result = {
            "application_switch_count": self._switch_count,
            "context_switches": self._switch_count,
            "meeting_minutes": round(self._meeting_seconds / 60, 1),
        }
        self._switch_count = 0
        self._meeting_seconds = 0.0
        return result
