from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.models import Role, User
from apps.backend.services import baseline_service
from shared.enums.roles import RoleName

router = APIRouter(prefix="/employees", tags=["employees"])


def _assert_self_or_admin(employee_id: str, user: User, db: Session) -> None:
    """Privacy rule (Phase 16): individual wellness data is visible only to
    the employee themselves or an org admin performing consent/compliance
    duties - never to a manager.

    Admin access is additionally scoped to the admin's own organization
    (Phase 20 tenant isolation): being an admin somewhere must not grant
    read access to another tenant's employees.
    """
    if user.id == employee_id:
        return

    role = db.get(Role, user.role_id)
    if role and role.name == RoleName.ADMIN.value:
        target = db.get(User, employee_id)
        if target and target.org_id == user.org_id:
            return
        raise HTTPException(status_code=403, detail="Employee is outside your organization")

    raise HTTPException(status_code=403, detail="Not authorized to view this employee's wellness data")


@router.get("/{employee_id}/baseline")
def get_baseline(employee_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_self_or_admin(employee_id, user, db)
    return baseline_service.get_baseline_response(db, employee_id)


@router.get("/{employee_id}/patterns")
def get_patterns(employee_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_self_or_admin(employee_id, user, db)
    return {"employee_id": employee_id, "patterns": baseline_service.get_patterns(db, employee_id)}
