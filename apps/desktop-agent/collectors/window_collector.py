import subprocess
import sys


def get_active_window_title() -> str | None:
    """Best-effort, OS-specific active window title lookup. Only the title
    is ever used, and only to derive a switch count / meeting-app match -
    the title itself is never uploaded (Phase 2.1: converted to a category
    signal, not stored as content). Returns None on any failure, including
    on platforms/sessions where this isn't available (e.g. headless)."""
    try:
        if sys.platform == "win32":
            import win32gui

            return win32gui.GetWindowText(win32gui.GetForegroundWindow()) or None

        if sys.platform == "darwin":
            from AppKit import NSWorkspace

            app = NSWorkspace.sharedWorkspace().activeApplication()
            return app.get("NSApplicationName") if app else None

        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


MEETING_KEYWORDS = ["zoom", "meet", "teams", "webex"]


def is_meeting_window(title: str | None) -> bool:
    if not title:
        return False
    lowered = title.lower()
    return any(keyword in lowered for keyword in MEETING_KEYWORDS)
