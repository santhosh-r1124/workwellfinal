from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import gen_id


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (UniqueConstraint("user_id", "source", name="uq_consent_user_source"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConsentEvent(Base):
    __tablename__ = "consent_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    previous_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    new_value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
