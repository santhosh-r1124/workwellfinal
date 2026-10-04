"""Org-published support resources (EAP lines, benefits portals, hotlines).

This is admin-authored *content*, not collected data: it is scoped to an org,
shown to everyone in it, and carries no telemetry. Kept out of admin_service
because it is a distinct concern with its own small CRUD, and the employee
side reads it too.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import SupportResource

# A resource's category. Plain groupings for display order and nothing more -
# never a severity, a condition, or anything that would read as a diagnosis.
CATEGORIES = ["crisis", "counselling", "benefits", "general"]
DEFAULT_CATEGORY = "general"


def _serialize(row: SupportResource) -> dict:
    return {
        "id": row.id,
        "label": row.label,
        "description": row.description,
        "category": row.category,
        "url": row.url,
        "phone": row.phone,
        "email": row.email,
        "sort_order": row.sort_order,
        "is_active": row.is_active,
    }


def list_for_org(db: Session, org_id: str, *, active_only: bool) -> list[dict]:
    """Ordered the way an employee should read them: crisis first regardless
    of sort_order, then by the admin's chosen order, then alphabetically so
    the list is stable when two share an order."""
    stmt = select(SupportResource).where(SupportResource.org_id == org_id)
    if active_only:
        stmt = stmt.where(SupportResource.is_active.is_(True))
    rows = list(db.scalars(stmt))
    rows.sort(key=lambda r: (r.category != "crisis", r.sort_order, r.label.lower()))
    return [_serialize(r) for r in rows]


def create(
    db: Session,
    org_id: str,
    *,
    label: str,
    description: str | None,
    category: str,
    url: str | None,
    phone: str | None,
    email: str | None,
    sort_order: int,
) -> dict:
    row = SupportResource(
        org_id=org_id,
        label=label,
        description=description,
        category=category if category in CATEGORIES else DEFAULT_CATEGORY,
        url=url,
        phone=phone,
        email=email,
        sort_order=sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


def delete(db: Session, org_id: str, resource_id: str) -> bool:
    """Scoped by org: a resource id alone must never let an admin in one org
    remove another org's resource."""
    row = db.get(SupportResource, resource_id)
    if row is None or row.org_id != org_id:
        return False
    db.delete(row)
    db.commit()
    return True
