from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    pattern_state_id: Mapped[str | None] = mapped_column(
        ForeignKey("pattern_states.id"), nullable=True
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    risk: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    intervention: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    wellness: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
