from sqlalchemy.orm import Session

from apps.backend.services import audit_service


def log_agent_run(db: Session, employee_id: str, agent_run_id: str, state: str, intervention_type: str) -> None:
    audit_service.record(
        db,
        actor_id=None,
        subject_user_id=employee_id,
        action="agent.orchestration_run",
        resource=f"agent_run:{agent_run_id}",
        meta={"state": state, "intervention_type": intervention_type},
    )
