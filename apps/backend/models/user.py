from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id

if TYPE_CHECKING:
    from apps.backend.models.organization import Organization


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), nullable=False)
    team: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Someone who has left must stop being analysed - continuing to profile
    # an ex-employee is both pointless and, in most jurisdictions, no longer
    # covered by the consent they gave. Deactivation stops the daily sweep
    # and invalidates their existing session on the next request; their
    # history stays until the retention window expires it.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Opting out of being emailed is not opting out of being helped: the
    # suggestion still appears on the dashboard. Kept on the user rather
    # than in the consent table because it governs delivery, not
    # collection, and conflating the two would let someone withdraw a
    # notification preference and believe they had withdrawn consent.
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Which day is "today" for this person. The product's whole unit of
    # analysis is a day, so a boundary drawn in the wrong place is not
    # cosmetic: someone thirteen hours from UTC would have their day cut
    # mid-afternoon, see a dashboard reading from the day before last, and
    # be analysed on a half-finished day. IANA name, set from the browser
    # at login; invalid or unknown values fall back to UTC.
    timezone: Mapped[str] = mapped_column(
        String, nullable=False, default="UTC", server_default="UTC"
    )

    organization: Mapped["Organization"] = relationship(back_populates="users")
