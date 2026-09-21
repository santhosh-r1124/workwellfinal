from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
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

    organization: Mapped["Organization"] = relationship(back_populates="users")
