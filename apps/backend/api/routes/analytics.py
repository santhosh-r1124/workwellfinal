from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_db, require_role
from apps.backend.models import User
from apps.backend.services import analytics_service, audit_service
from shared.enums.roles import RoleName

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Managers get the inverse of the individual-data rule: aggregates yes,
# individuals never (see api/routes/employees.py for the other half).
_manager_or_admin = require_role(RoleName.MANAGER.value, RoleName.ADMIN.value)


@router.get("/teams")
def list_teams(user: User = Depends(_manager_or_admin), db: Session = Depends(get_db)):
    return {"teams": analytics_service.list_teams(db, user.org_id)}


@router.get("/wellness-overview")
def wellness_overview(user: User = Depends(_manager_or_admin), db: Session = Depends(get_db)):
    result = analytics_service.wellness_overview(db, user.org_id)
    audit_service.record(
        db,
        actor_id=user.id,
        subject_user_id=None,
        action="analytics.wellness_view",
        resource="org:wellness",
        meta={"cohort_size": result["cohort_size"], "sufficient": result["sufficient_cohort"]},
    )
    return result


@router.get("/teams/{team}")
def team_analytics(
    team: str, user: User = Depends(_manager_or_admin), db: Session = Depends(get_db)
):
    # Scoped to the caller's own org, so a manager cannot read another
    # tenant's teams by guessing a team name.
    result = analytics_service.team_analytics(db, user.org_id, team)

    audit_service.record(
        db,
        actor_id=user.id,
        subject_user_id=None,
        action="analytics.team_view",
        resource=f"team:{team}",
        meta={"cohort_size": result["cohort_size"], "sufficient": result["sufficient_cohort"]},
    )
    return result
