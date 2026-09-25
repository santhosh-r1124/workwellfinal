"""Org-level policy, enforced in one place.

Three admin toggles were stored and rendered but never consulted:
`disabled_sources`, `interventions_enabled` and `allowed_integrations`. A
switch in an admin panel that changes nothing is worse than no switch -
it is a compliance answer the product cannot honour. This module is the
single point where those settings become real, so the enforcement cannot
drift between the consent API, ingestion, the agent pipeline and the
integration framework.

The direction of travel is one-way: org policy only ever *subtracts*
collection. An admin can switch a source off for everyone; no admin
setting can switch one on for an employee who declined it, and none can
re-enable a source the code marks never-collectible.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import OrgSettings, User


def settings_for_org(db: Session, org_id: str) -> OrgSettings | None:
    return db.scalar(select(OrgSettings).where(OrgSettings.org_id == org_id))


def settings_for_user(db: Session, user_id: str) -> OrgSettings | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    return settings_for_org(db, user.org_id)


def disabled_sources_for_user(db: Session, user_id: str) -> set[str]:
    settings = settings_for_user(db, user_id)
    if settings is None:
        return set()
    return {str(s) for s in (settings.disabled_sources or [])}


def interventions_enabled(db: Session, user_id: str) -> bool:
    """False puts the org in observe-only mode: employees still see their
    own dashboard and explanation, but the system proposes no nudges and
    sends no notifications. Some deployments need this while works
    councils or unions review the rollout."""
    settings = settings_for_user(db, user_id)
    return True if settings is None else bool(settings.interventions_enabled)


def integration_allowed(db: Session, org_id: str, connector_key: str) -> bool:
    """An empty allowlist means 'no restriction', not 'nothing allowed' -
    otherwise a fresh org, whose settings row is created with defaults,
    would silently have every connector blocked."""
    settings = settings_for_org(db, org_id)
    if settings is None:
        return True
    allowed = [str(k) for k in (settings.allowed_integrations or [])]
    return True if not allowed else connector_key in allowed
