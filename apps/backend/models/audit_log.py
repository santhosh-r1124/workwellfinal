from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    subject_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource: Mapped[str] = mapped_column(String, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
