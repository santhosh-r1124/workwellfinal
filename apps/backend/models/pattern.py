from datetime import date as date_type

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class PatternStateRecord(Base, TimestampMixin):
    __tablename__ = "pattern_states"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    duration_days: Mapped[int] = mapped_column(Integer, default=0)
    signals: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
