import signal
import sys
import time
from datetime import datetime, timezone

import requests
from collectors.activity_collector import ActivityCollector
from collectors.window_tracker import WindowTracker
from config import AgentConfig
from privacy.consent_gate import ConsentGate
from processors.session_tracker import SessionTracker

TICK_SECONDS = 30


def send_event(config: AgentConfig, features: dict) -> None:
    payload = {
        "employee_id": config.employee_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": features,
    }
    try:
        requests.post(
            f"{config.backend_url}/telemetry/events",
            json=payload,
            headers={"Authorization": f"Bearer {config.agent_token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        print(f"[workwell-agent] failed to send telemetry: {exc}", file=sys.stderr)


def collect_features(gate: ConsentGate, session: SessionTracker, window_tracker: WindowTracker, activity: ActivityCollector) -> dict:
    features: dict = {}

    if gate.allows("working_hours") or gate.allows("break_patterns"):
        window_result = session.drain_window(TICK_SECONDS)
        if gate.allows("working_hours"):
            features["active_minutes"] = window_result["active_minutes"]
            features["idle_minutes"] = window_result["idle_minutes"]
            features["continuous_session_minutes"] = window_result["continuous_session_minutes"]
        if gate.allows("break_patterns"):
            features["break_minutes"] = window_result["break_minutes"]

    if gate.allows("application_categories") or gate.allows("calendar_metadata"):
        window_features = window_tracker.drain_window()
        if gate.allows("application_categories"):
            features["application_switch_count"] = window_features["application_switch_count"]
            features["context_switches"] = window_features["context_switches"]
        if gate.allows("calendar_metadata"):
            features["meeting_minutes"] = window_features["meeting_minutes"]

    if gate.allows("typing_dynamics"):
        features.update(activity.drain_window())

    return features


def run() -> None:
    config = AgentConfig()
    gate = ConsentGate(config.consent)

    activity = ActivityCollector()
    activity.start()
    window_tracker = WindowTracker(poll_interval_seconds=TICK_SECONDS)
    session = SessionTracker()

    running = True

    def handle_stop(*_args) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    if not config.employee_id or not config.agent_token:
        print(
            "[workwell-agent] WORKWELL_EMPLOYEE_ID and WORKWELL_AGENT_TOKEN must be set - "
            "see .env.example. Exiting.",
            file=sys.stderr,
        )
        return

    print(f"[workwell-agent] starting for {config.employee_id}, reporting every {config.report_interval_seconds}s")

    elapsed_since_report = 0
    while running:
        time.sleep(TICK_SECONDS)

        if gate.allows("working_hours") or gate.allows("break_patterns"):
            session.record_tick(activity.seconds_since_last_input(), TICK_SECONDS)
        if gate.allows("application_categories") or gate.allows("calendar_metadata"):
            window_tracker.poll_once()

        elapsed_since_report += TICK_SECONDS
        if elapsed_since_report >= config.report_interval_seconds:
            features = collect_features(gate, session, window_tracker, activity)
            if features:
                send_event(config, features)
            elapsed_since_report = 0

    activity.stop()
    print("[workwell-agent] stopped")


if __name__ == "__main__":
    run()
