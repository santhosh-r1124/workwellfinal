import sys
from pathlib import Path

DESKTOP_AGENT_ROOT = Path(__file__).resolve().parents[2] / "apps" / "desktop-agent"
if str(DESKTOP_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(DESKTOP_AGENT_ROOT))

from collectors.activity_collector import summarize_keystrokes  # noqa: E402
from collectors.window_collector import is_meeting_window  # noqa: E402
from processors.session_tracker import SessionTracker  # noqa: E402


def test_summarize_keystrokes_empty():
    result = summarize_keystrokes([], backspace_count=0, key_count=0)
    assert result["typing_speed"] == 0.0


def test_summarize_keystrokes_computes_pause_rate_and_backspace_rate():
    timestamps = [0, 0.5, 1.0, 5.0, 5.5]
    result = summarize_keystrokes(timestamps, backspace_count=1, key_count=5)
    assert result["pause_rate"] == 0.25
    assert result["backspace_rate"] == 0.2


def test_session_tracker_registers_break_after_sustained_idle():
    tracker = SessionTracker()
    for _ in range(15):
        tracker.record_tick(idle_seconds=999, tick_seconds=30)
    result = tracker.drain_window(30)
    assert result["break_minutes"] > 0
    assert result["active_minutes"] == 0.0


def test_session_tracker_tracks_longest_active_streak():
    tracker = SessionTracker()
    for _ in range(5):
        tracker.record_tick(idle_seconds=0, tick_seconds=30)
    tracker.record_tick(idle_seconds=999, tick_seconds=30)
    result = tracker.drain_window(30)
    assert result["continuous_session_minutes"] == 2.5


def test_is_meeting_window_matches_known_apps():
    assert is_meeting_window("Zoom Meeting")
    assert not is_meeting_window("Visual Studio Code")
    assert not is_meeting_window(None)
