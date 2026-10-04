from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class SupportResource(Base, TimestampMixin):
    """An org-configured place an employee can go for help - an EAP line, a
    benefits portal, a crisis hotline. Deliberately *not* collected data: it
    is content an admin publishes, carries no telemetry, and is shown to the
    whole org rather than being personal. It exists so the dashboard and chat
    can point somewhere real instead of ending at "consider reaching out".

    No clinical labelling here either: a resource has a plain label and a
    category, never a severity or a condition it is "for".
    """

    __tablename__ = "support_resources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)

    label: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # One of CATEGORIES below. Stored as a string rather than a DB enum so
    # adding a category is a code change, not a migration.
    category: Mapped[str] = mapped_column(String, nullable=False, default="general")

    # Contact routes, all optional so a resource can be pure text. A URL
    # opens in a new tab; a phone shows as a tel: link; an email as a mailto:
    # link. An org typically fills in its company number and company email.
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)

    # Lower sorts first. Lets an admin put the crisis line above the gym
    # discount without renaming anything.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Hidden rather than deleted, so a resource can be retired without losing
    # the row an audit entry might reference.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
