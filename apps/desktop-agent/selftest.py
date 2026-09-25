"""Check what actually works on this machine, before trusting it.

The collectors are best-effort per platform - win32gui, AppKit, xdotool -
and each returns None where it cannot work rather than raising. That is
the right behaviour for a background agent and the wrong behaviour for a
rollout: an agent whose window tracking silently returns None all day
still uploads, still looks healthy, and quietly reports zero context
switches for everyone on that OS. Zero is indistinguishable from
"nobody switched windows", so the baseline learns it and the product
concludes nothing is ever wrong.

So: run this once on each OS you intend to support, before anyone relies
on the numbers.

    python apps/desktop-agent/selftest.py
"""

from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from collectors.window_collector import get_active_window_title  # noqa: E402
from config import DEFAULT_CONSENT, AgentConfig  # noqa: E402
from privacy.consent_gate import ConsentGate  # noqa: E402
from processors.session_tracker import SessionTracker  # noqa: E402

OK = "  ok  "
WARN = " warn "
FAIL = " FAIL "


def report(level: str, name: str, detail: str) -> None:
    print(f"{level}  {name}: {detail}")


def check_platform() -> None:
    report(OK, "platform", f"{platform.system()} {platform.release()} / Python {platform.python_version()}")
    if not os.environ.get("DISPLAY") and sys.platform not in ("win32", "darwin"):
        report(
            WARN,
            "display",
            "no DISPLAY set - window tracking cannot work in a headless session",
        )


def check_window_tracking() -> bool:
    """The signal most likely to fail silently."""
    title = get_active_window_title()
    if title is None:
        report(
            FAIL,
            "active window",
            "unavailable - context switches and meeting time will read as zero all day, "
            "which the baseline will learn as this person's normal",
        )
        if sys.platform == "win32":
            print("        install pywin32")
        elif sys.platform == "darwin":
            print("        install pyobjc; macOS may also need Accessibility permission")
        else:
            print("        install xdotool, and check this is an X session rather than Wayland")
        return False

    # The title itself never leaves the machine; only its length is shown
    # here, so a self-test screenshot cannot leak what someone is reading.
    report(OK, "active window", f"readable ({len(title)} characters, never uploaded)")
    return True


def check_input_activity() -> bool:
    try:
        from collectors.activity_collector import ActivityCollector
    except Exception as exc:
        report(FAIL, "input activity", f"pynput unavailable: {type(exc).__name__}")
        print("        install pynput; macOS needs Input Monitoring permission")
        return False

    collector = ActivityCollector()
    try:
        collector.start()
    except Exception as exc:
        report(FAIL, "input activity", f"could not start listeners: {type(exc).__name__}")
        return False

    print("        type something for three seconds...")
    time.sleep(3)
    window = collector.drain_window()
    collector.stop()

    if not window or not any(window.values()):
        report(
            WARN,
            "input activity",
            "listeners started but recorded nothing - either nobody typed, or the OS "
            "is withholding input events from this process",
        )
        return False

    report(OK, "input activity", "recorded timing only, never which keys")
    return True


def check_idle_detection() -> bool:
    session = SessionTracker()
    for _ in range(4):
        session.record_tick(idle_seconds=0, tick_seconds=30)
    for _ in range(12):
        session.record_tick(idle_seconds=600, tick_seconds=30)
    window = session.drain_window(tick_seconds=30)

    if not window or window.get("active_minutes", 0) <= 0:
        report(FAIL, "idle detection", "session tracker produced nothing")
        return False

    report(
        OK,
        "idle detection",
        f"{window['active_minutes']}m active / {window['idle_minutes']}m idle "
        f"/ {window['break_minutes']}m break, from synthetic ticks",
    )
    return True


def check_config() -> bool:
    config = AgentConfig()
    problems = []
    if not config.agent_token:
        problems.append("WORKWELL_AGENT_TOKEN")
    if not config.employee_id:
        problems.append("WORKWELL_EMPLOYEE_ID")

    if problems:
        report(WARN, "configuration", f"not set: {', '.join(problems)}")
        print("        register a device in Privacy Centre -> Your devices")
        return False

    report(OK, "configuration", f"reporting to {config.backend_url} every {config.report_interval_seconds}s")
    return True


def check_consent_gate() -> bool:
    """The gate is what keeps a disabled signal from even being computed.
    If it ever stopped filtering, the server-side strip would still catch
    it - but defence in depth only counts while both layers work."""
    gate = ConsentGate({**DEFAULT_CONSENT, "typing_dynamics": False})
    if gate.allows("typing_dynamics"):
        report(FAIL, "consent gate", "a disabled source was allowed - do not run this agent")
        return False
    if not gate.allows("working_hours"):
        report(FAIL, "consent gate", "an enabled source was blocked")
        return False

    report(OK, "consent gate", "disabled sources are not collected on-device")
    return True


def main() -> int:
    print("WorkWell desktop agent - self test\n")
    check_platform()
    print()

    results = {
        "consent gate": check_consent_gate(),
        "idle detection": check_idle_detection(),
        "active window": check_window_tracking(),
        "input activity": check_input_activity(),
        "configuration": check_config(),
    }

    print()
    blocking = [name for name in ("consent gate", "idle detection") if not results[name]]
    degraded = [name for name, ok in results.items() if not ok and name not in blocking]

    if blocking:
        print(f"Do not deploy on this platform: {', '.join(blocking)} failed.")
        return 2
    if degraded:
        print(
            f"Usable, but {', '.join(degraded)} will report nothing on this machine.\n"
            "Signals that are always zero get learned as normal, so fix these before "
            "relying on the numbers."
        )
        return 1

    print("Everything this agent collects works on this machine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
