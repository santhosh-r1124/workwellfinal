"""A model outage must cost prose, not evidence.

Every figure this product shows is computed by ml/. The provider only turns
those figures into sentences, so a revoked key or a bad gateway should
degrade the wording and leave the detection intact.
"""

from datetime import date, timedelta

import pytest

from agents import context_agent, intervention_agent, wellness_agent
from agents.narration import safe_generate
from agents.orchestrator import run_orchestration
from apps.backend.models import DailyFeature
from tests.integration.conftest import auth_headers, make_user


class BrokenProvider:
    """Stands in for a revoked key, a 503, or a changed response shape."""

    def generate(self, prompt: str, system: str | None = None) -> str:
        raise RuntimeError("provider unavailable")

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("provider unavailable")


class EmptyProvider:
    def generate(self, prompt: str, system: str | None = None) -> str:
        return "   "

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 768 for _ in texts]


def _seed_strained_history(db_session, employee_id: str) -> None:
    today = date.today()
    for offset in range(24, 0, -1):
        shifted = offset <= 8
        db_session.add(
            DailyFeature(
                employee_id=employee_id,
                date=today - timedelta(days=offset),
                work_duration=11.0 if shifted else 8.0,
                after_hours=3.2 if shifted else 0.3,
                break_count=2 if shifted else 4,
                average_break_gap=220.0 if shifted else 100.0,
                meeting_hours=1.5,
                context_switches=30,
                focus_minutes=150.0 if shifted else 200.0,
                typing_speed=50.0,
                typing_pause_rate=0.15,
                derived={
                    "meeting_load": 0.19,
                    "recovery_gap": 2.2 if shifted else 0.0,
                    "context_switch_rate": 3.75,
                    "focus_fragmentation": 0.4,
                    "typing_deviation": 0.0,
                },
            )
        )
    db_session.commit()


def test_safe_generate_returns_fallback_instead_of_raising():
    text, narrated = safe_generate(BrokenProvider(), "prompt", "system", "fallback text")
    assert text == "fallback text"
    assert narrated is False


def test_safe_generate_treats_blank_output_as_unavailable():
    text, narrated = safe_generate(EmptyProvider(), "prompt", "system", "fallback text")
    assert text == "fallback text"
    assert narrated is False


def test_intervention_still_chosen_without_the_model():
    """Which intervention fires is a rule, not a generation."""
    risk = {
        "state": "PATTERN_CHANGE",
        "component_scores": {"recovery_strain": 0.9, "schedule_strain": 0.1},
    }
    result = intervention_agent.propose_intervention(risk, BrokenProvider())

    assert result["type"] == "recovery_break"
    assert result["narrated"] is False
    assert result["message"] == result["rationale"]


def test_context_labels_survive_the_model_being_down(monkeypatch):
    monkeypatch.setattr("agents.providers.get_provider", lambda: BrokenProvider())
    pattern = {"signals": [{"name": "meeting_load", "change": 0.5, "anomalous_days": 6}]}

    result = context_agent.analyze_context(pattern)

    assert result["likely_context"] == ["meeting_increase"]
    assert result["narrated"] is False
    assert "meeting increase" in result["explanation"]


def test_wellness_falls_back_to_the_rationale(db_session, org):
    employee = make_user(db_session, org, "employee", "outage_well", "outage_well@example.com")
    pattern = {"signals": [{"name": "recovery_gap", "change": 1.4, "anomalous_days": 6}]}
    intervention = {"type": "recovery_break", "rationale": "Break frequency has dropped."}

    result = wellness_agent.build_recommendation(
        db_session, pattern, {"likely_context": []}, intervention, BrokenProvider()
    )

    assert result["narrated"] is False
    assert result["recommendation"] == "Break frequency has dropped."
    assert employee.id  # fixture used


def test_orchestration_completes_and_flags_degradation(db_session, org, monkeypatch):
    employee = make_user(db_session, org, "employee", "outage_orch", "outage_orch@example.com")
    _seed_strained_history(db_session, employee.id)

    monkeypatch.setattr("agents.providers.get_provider", lambda: BrokenProvider())
    monkeypatch.setattr("agents.orchestrator.get_provider", lambda: BrokenProvider())

    result = run_orchestration(db_session, employee.id)

    # The detection half is untouched.
    assert result["pattern"]["state"] == "PATTERN_CHANGE"
    assert result["pattern"]["signals"]
    assert result["risk"]["state"] in ("PATTERN_CHANGE", "SUSTAINED_STRAIN", "SUPPORT_RECOMMENDED")
    assert result["intervention"]["type"] != "no_action"
    # ...and the employee is told the prose is missing rather than shown a fallback as if generated.
    assert result["narrative_degraded"] is True


def test_chat_endpoint_does_not_500_during_an_outage(app_client, db_session, org, monkeypatch):
    employee = make_user(db_session, org, "employee", "outage_chat", "outage_chat@example.com")
    _seed_strained_history(db_session, employee.id)

    monkeypatch.setattr("agents.providers.get_provider", lambda: BrokenProvider())
    monkeypatch.setattr("agents.orchestrator.get_provider", lambda: BrokenProvider())

    headers = auth_headers(app_client, "outage_chat@example.com")
    res = app_client.post("/chat", json={"employee_id": "", "message": "why?"}, headers=headers)

    assert res.status_code == 200
    assert res.json()["reply"]
    assert employee.id


@pytest.mark.parametrize("message", ["I want to kill myself", "I've been feeling hopeless"])
def test_safety_replies_even_when_the_model_is_down(
    app_client, db_session, org, monkeypatch, message
):
    """The safety path is deterministic by design - it must not depend on a
    provider being reachable."""
    suffix = abs(hash(message)) % 10000
    make_user(db_session, org, "employee", f"outage_safe_{suffix}", f"outage_safe_{suffix}@example.com")

    monkeypatch.setattr("agents.providers.get_provider", lambda: BrokenProvider())
    monkeypatch.setattr("agents.orchestrator.get_provider", lambda: BrokenProvider())

    headers = auth_headers(app_client, f"outage_safe_{suffix}@example.com")
    res = app_client.post("/chat", json={"employee_id": "", "message": message}, headers=headers)

    assert res.status_code == 200
    assert res.json()["safety_flagged"] is True
    assert "988" in res.json()["reply"] or "Employee Assistance" in res.json()["reply"]
