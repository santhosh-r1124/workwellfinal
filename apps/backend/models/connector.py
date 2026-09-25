from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class ConnectorConfig(TimestampMixin, Base):
    """An employee's own connection to an outside source.

    Configured by them, in their Privacy Centre, not by an administrator:
    the credential is theirs, it grants access to their calendar, and
    nobody else should be able to attach one on their behalf.
    """

    __tablename__ = "connector_configs"
    __table_args__ = (UniqueConstraint("employee_id", "connector_key", name="uq_connector_per_employee"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    connector_key: Mapped[str] = mapped_column(String, nullable=False)

    # Fernet ciphertext, never plaintext - see apps/backend/core/crypto.py.
    encrypted_config: Mapped[str] = mapped_column(String, nullable=False)
    # A redacted hint so the employee can tell which URL is stored without
    # the URL itself being readable from the database or the API.
    config_hint: Mapped[str] = mapped_column(String, nullable=False, default="")

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_sync_detail: Mapped[str | None] = mapped_column(String, nullable=True)
