from sqlalchemy.orm import Session

from agents import audit_agent, context_agent, intervention_agent, wellness_agent
from agents.privacy_agent import has_sufficient_consent
from agents.providers import get_provider
from apps.backend.core.observability import record_intervention, record_intervention_suppressed
from apps.backend.repositories import agent_repo, baseline_repo, chat_repo
from apps.backend.services import baseline_service, org_policy
from ml.risk.risk_fusion import compute_component_scores, fuse_risk
from shared.constants.wellbeing import INTERVENTION_COOLDOWN_DAYS, PERSISTENCE_MIN_DAYS


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

    # A scheduled run has no one to ask, so it reuses the last thing the
    # employee volunteered. Otherwise "it's because of a release" would
    # have to be re-explained every single day.
    note = employee_note or chat_repo.latest_employee_note(db, employee_id)
    context = context_agent.analyze_context(pattern, note)

    component_scores = compute_component_scores(pattern.get("signals", []))
    risk = fuse_risk(component_scores, persistent, self_report_strain=0.0, safety_flag=False)

    intervention = intervention_agent.propose_intervention(risk, provider)

    wellness = wellness_agent.build_recommendation(db, pattern, context, intervention, provider)

    pattern_states = baseline_repo.recent_pattern_states(db, employee_id, limit=1)
    pattern_state_id = pattern_states[-1].id if pattern_states else None

    agent_run = agent_repo.create_agent_run(
        db, employee_id, pattern_state_id, context, risk, intervention, wellness
    )

    # The run is always recorded; the nudge is not. Once this runs on a
    # daily schedule rather than only when someone opens the chat, an
    # unchanged persistent pattern would otherwise produce an identical
    # nudge every morning.
    intervention_id = None
    suppressed = False
    if intervention["type"] != "no_action" and not org_policy.interventions_enabled(db, employee_id):
        # Observe-only org: the analysis is still stored and the employee
        # can still see their own dashboard, but nothing nudges them.
        suppressed = True
        record_intervention_suppressed(intervention["type"])
    elif intervention["type"] != "no_action":
        existing = agent_repo.intervention_within_cooldown(
            db, employee_id, intervention["type"], INTERVENTION_COOLDOWN_DAYS
        )
        if existing:
            suppressed = True
            record_intervention_suppressed(intervention["type"])
        else:
            intervention_id = agent_repo.create_intervention(
                db, employee_id, agent_run.id, intervention["type"], intervention["message"]
            ).id

    record_intervention(intervention["type"])
    audit_agent.log_agent_run(db, employee_id, agent_run.id, risk["state"], intervention["type"])

    # True when the model couldn't be reached for any step. The evidence is
    # still complete - only the prose around it is missing - and the UI says
    # so rather than passing a fallback off as a generated explanation.
    narrative_degraded = not all(
        step.get("narrated", True) for step in (context, intervention, wellness)
    )

    return {
        "employee_id": employee_id,
        "pattern": pattern,
        "context": context,
        "risk": risk,
        "intervention": intervention,
        "wellness": wellness,
        "narrative_degraded": narrative_degraded,
        "agent_run_id": agent_run.id,
        "intervention_id": intervention_id,
        "intervention_suppressed": suppressed,
    }
