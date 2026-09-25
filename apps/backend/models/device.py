from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class DeviceToken(Base, TimestampMixin):
    """One credential per machine, bound to one employee.

    Replaces a shared device token. With a shared secret the agent also
    had to name the employee it was reporting for, which meant anyone who
    could read an agent's config - it sits in a file on their own laptop -
    could post fabricated telemetry as any colleague. In a product whose
    output is "this person's work pattern has changed", that is the worst
    available bug.

    The token is stored as a SHA-256 digest rather than a bcrypt hash: it
    is 256 bits from `secrets`, not a human-chosen password, so there is
    no dictionary to slow down, and this is checked on every ingest.
    """

    __tablename__ = "device_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
