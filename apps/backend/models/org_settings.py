from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import gen_id

DEFAULT_RETENTION_DAYS = 90
DEFAULT_MIN_COHORT = 5


class OrgSettings(Base):
    """Administrator-controlled org policy (Phase 12). Defaults here are the
    privacy-protective ones; an admin can tighten them but the code-level
    guarantees (never-collectible sources, per-metric cohort floor) are not
    configurable away."""

    __tablename__ = "org_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), unique=True, nullable=False)

    retention_days: Mapped[int] = mapped_column(Integer, default=DEFAULT_RETENTION_DAYS)
    aggregation_min_cohort: Mapped[int] = mapped_column(Integer, default=DEFAULT_MIN_COHORT)

    interventions_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Consent sources an admin has disabled org-wide. Employees can still
    # turn off anything else individually; this only ever subtracts.
    disabled_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    allowed_integrations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
