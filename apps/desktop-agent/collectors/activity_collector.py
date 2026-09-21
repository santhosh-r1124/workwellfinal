import time
from collections import deque
from threading import Lock

try:
    from pynput import keyboard, mouse

    PYNPUT_AVAILABLE = True
except Exception:  # pynput needs a display/input backend; unavailable headless
    PYNPUT_AVAILABLE = False

PAUSE_THRESHOLD_SECONDS = 2.0


def summarize_keystrokes(timestamps: list[float], backspace_count: int, key_count: int) -> dict:
    """Pure function over already-anonymized timing data (no key content),
    kept separate from the listener so it can be unit tested without a
    display server."""
    if len(timestamps) < 2 or key_count == 0:
        return {
            "typing_speed": 0.0,
            "inter_key_interval": 0.0,
            "pause_rate": 0.0,
            "backspace_rate": 0.0,
            "correction_rate": 0.0,
            "typing_burst_length": 0.0,
        }

    intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
    pauses = [i for i in intervals if i > PAUSE_THRESHOLD_SECONDS]
    duration_minutes = max((timestamps[-1] - timestamps[0]) / 60, 1 / 60)

    bursts = []
    current_burst = 1
    for interval in intervals:
        if interval <= PAUSE_THRESHOLD_SECONDS:
            current_burst += 1
        else:
            bursts.append(current_burst)
            current_burst = 1
    bursts.append(current_burst)

    return {
        "typing_speed": round(key_count / duration_minutes, 1),
        "inter_key_interval": round(sum(intervals) / len(intervals), 3),
        "pause_rate": round(len(pauses) / len(intervals), 3),
        "backspace_rate": round(backspace_count / key_count, 3),
        "correction_rate": round(backspace_count / key_count, 3),
        "typing_burst_length": round(sum(bursts) / len(bursts), 1),
    }


class ActivityCollector:
    """Tracks keystroke TIMING and structural key type (e.g. backspace) only
    - never the character typed - plus mouse activity timestamps for idle
    detection. Raw input is folded into these counters and discarded
    continuously; nothing here is ever persisted to disk."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._key_timestamps: deque[float] = deque(maxlen=5000)
        self._backspace_count = 0
        self._key_count = 0
        self._last_input_ts = time.time()
        self._listeners: list = []

    def start(self) -> None:
        if not PYNPUT_AVAILABLE:
            return
        kb_listener = keyboard.Listener(on_press=self._on_key)
        m_listener = mouse.Listener(on_move=self._on_mouse, on_click=self._on_mouse)
        kb_listener.start()
        m_listener.start()
        self._listeners = [kb_listener, m_listener]

    def stop(self) -> None:
        for listener in self._listeners:
            listener.stop()
        self._listeners = []

    def _on_key(self, key) -> None:
        now = time.time()
        with self._lock:
            self._key_timestamps.append(now)
            self._key_count += 1
            if key in (keyboard.Key.backspace, keyboard.Key.delete):
                self._backspace_count += 1
            self._last_input_ts = now

    def _on_mouse(self, *_args) -> None:
        with self._lock:
            self._last_input_ts = time.time()

    def seconds_since_last_input(self) -> float:
        with self._lock:
            return time.time() - self._last_input_ts

    def drain_window(self) -> dict:
        with self._lock:
            timestamps = list(self._key_timestamps)
            backspace_count = self._backspace_count
            key_count = self._key_count
            self._key_timestamps.clear()
            self._backspace_count = 0
            self._key_count = 0
        return summarize_keystrokes(timestamps, backspace_count, key_count)
