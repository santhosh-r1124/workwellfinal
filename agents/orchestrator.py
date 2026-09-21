from sqlalchemy.orm import Session

from agents import audit_agent, context_agent, intervention_agent, wellness_agent
from agents.privacy_agent import has_sufficient_consent
from agents.providers import get_provider
from apps.backend.core.observability import record_intervention
from apps.backend.repositories import agent_repo, baseline_repo
from apps.backend.services import baseline_service
from ml.risk.risk_fusion import compute_component_scores, fuse_risk
from shared.constants.wellbeing import PERSISTENCE_MIN_DAYS


def run_orchestration(db: Session, employee_id: str, employee_note: str | None = None) -> dict:
    """Fixed workflow (Phase 6.1). The LLM never chooses the next step - this
    function does. Each agent is called in order and only explains or
    contextualizes evidence the deterministic layers (ml/) already computed.

    START -> consent check -> data quality -> pattern analysis -> context ->
    risk fusion -> (safety is a separate, independent pipeline; see
    agents/safety_agent.py) -> intervention -> RAG/wellness -> persist -> audit
    """
    provider = get_provider()

    if not has_sufficient_consent(db, employee_id):
        return {
            "employee_id": employee_id,
            "state": "NO_CONSENT",
            "message": "Insufficient consent to run analysis. Enable at least one behavioral signal in the Privacy Center.",
        }

    pattern = baseline_service.recompute_baselines(db, employee_id)
    if not pattern:
        return {
            "employee_id": employee_id,
            "state": "INSUFFICIENT_DATA",
            "message": "Not enough history yet to establish a personal baseline.",
        }

    persistent = pattern.get("duration_days", 0) >= PERSISTENCE_MIN_DAYS

    context = context_agent.analyze_context(pattern, employee_note)

    component_scores = compute_component_scores(pattern.get("signals", []))
    risk = fuse_risk(component_scores, persistent, self_report_strain=0.0, safety_flag=False)

    intervention = intervention_agent.propose_intervention(risk, provider)

    wellness = wellness_agent.build_recommendation(db, pattern, context, intervention, provider)

    pattern_states = baseline_repo.recent_pattern_states(db, employee_id, limit=1)
    pattern_state_id = pattern_states[-1].id if pattern_states else None

    agent_run = agent_repo.create_agent_run(
        db, employee_id, pattern_state_id, context, risk, intervention, wellness
    )
    if intervention["type"] != "no_action":
        agent_repo.create_intervention(
            db, employee_id, agent_run.id, intervention["type"], intervention["message"]
        )

    record_intervention(intervention["type"])
    audit_agent.log_agent_run(db, employee_id, agent_run.id, risk["state"], intervention["type"])

    return {
        "employee_id": employee_id,
        "pattern": pattern,
        "context": context,
        "risk": risk,
        "intervention": intervention,
        "wellness": wellness,
        "agent_run_id": agent_run.id,
    }
