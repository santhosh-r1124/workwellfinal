from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class SafetyEvent(Base, TimestampMixin):
    __tablename__ = "safety_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    chat_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("chat_messages.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    action_taken: Mapped[str] = mapped_column(String, nullable=False)
