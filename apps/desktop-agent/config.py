import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG_PATH = Path.home() / ".workwell" / "agent_config.json"

# Mirrors the Privacy Center's default toggles (Phase 1.1). This local copy
# lets the agent avoid even collecting a disabled signal; the backend
# enforces the same gates again server-side (shared/constants/data_sources.py
# FIELD_GATES) as the source of truth.
DEFAULT_CONSENT = {
    "working_hours": True,
    "break_patterns": True,
    "application_categories": True,
    "typing_dynamics": True,
    "calendar_metadata": False,
}


class AgentConfig:
    def __init__(self) -> None:
        self.backend_url = os.environ.get("WORKWELL_BACKEND_URL", "http://localhost:8000")
        # A per-device token, provisioned by the employee themselves in the
        # Privacy Centre ("Your devices") and shown once. It is bound to one
        # account server-side, so this machine can only ever report for the
        # person who registered it - and revoking it there stops this agent
        # immediately.
        self.agent_token = os.environ.get("WORKWELL_AGENT_TOKEN", "")
        self.employee_id = os.environ.get("WORKWELL_EMPLOYEE_ID", "")
        self.report_interval_seconds = int(os.environ.get("WORKWELL_REPORT_INTERVAL_SECONDS", "300"))
        self.consent = self._load_consent()

    def _load_consent(self) -> dict:
        if DEFAULT_CONFIG_PATH.exists():
            try:
                return {**DEFAULT_CONSENT, **json.loads(DEFAULT_CONFIG_PATH.read_text())}
            except (json.JSONDecodeError, OSError):
                pass
        return dict(DEFAULT_CONSENT)

    def save_consent(self, consent: dict) -> None:
        DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_CONFIG_PATH.write_text(json.dumps(consent, indent=2))
        self.consent = consent
