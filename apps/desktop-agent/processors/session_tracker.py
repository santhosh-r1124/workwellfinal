TICK_SECONDS = 30
IDLE_THRESHOLD_SECONDS = 120
BREAK_THRESHOLD_SECONDS = 300


class SessionTracker:
    """Turns a stream of idle/active ticks into work_duration-shaped
    features. Every tick is discarded immediately after folding into these
    running counters (Phase 2.1: raw events -> features -> discard raw)."""

    def __init__(self) -> None:
        self._active_ticks = 0
        self._idle_ticks = 0
        self._break_minutes = 0.0
        self._longest_active_streak_ticks = 0
        self._current_streak_ticks = 0
        self._consecutive_idle_ticks = 0

    def record_tick(self, idle_seconds: float, tick_seconds: float = TICK_SECONDS) -> None:
        if idle_seconds < IDLE_THRESHOLD_SECONDS:
            self._active_ticks += 1
            self._current_streak_ticks += 1
            self._longest_active_streak_ticks = max(
                self._longest_active_streak_ticks, self._current_streak_ticks
            )
            self._consecutive_idle_ticks = 0
        else:
            self._idle_ticks += 1
            self._current_streak_ticks = 0
            self._consecutive_idle_ticks += 1
            if self._consecutive_idle_ticks * tick_seconds >= BREAK_THRESHOLD_SECONDS:
                self._break_minutes += tick_seconds / 60

    def drain_window(self, tick_seconds: float = TICK_SECONDS) -> dict:
        result = {
            "active_minutes": round(self._active_ticks * tick_seconds / 60, 1),
            "idle_minutes": round(self._idle_ticks * tick_seconds / 60, 1),
            "break_minutes": round(self._break_minutes, 1),
            "continuous_session_minutes": round(self._longest_active_streak_ticks * tick_seconds / 60, 1),
        }
        self.__init__()
        return result
