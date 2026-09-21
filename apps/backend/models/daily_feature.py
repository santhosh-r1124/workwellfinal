from datetime import date as date_type

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class DailyFeature(Base, TimestampMixin):
    __tablename__ = "daily_features"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_daily_feature_employee_date"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)

    work_duration: Mapped[float] = mapped_column(Float, default=0.0)
    after_hours: Mapped[float] = mapped_column(Float, default=0.0)
    break_count: Mapped[int] = mapped_column(Integer, default=0)
    average_break_gap: Mapped[float] = mapped_column(Float, default=0.0)
    meeting_hours: Mapped[float] = mapped_column(Float, default=0.0)
    context_switches: Mapped[int] = mapped_column(Integer, default=0)
    focus_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    typing_speed: Mapped[float] = mapped_column(Float, default=0.0)
    typing_pause_rate: Mapped[float] = mapped_column(Float, default=0.0)

    self_report_stress: Mapped[float | None] = mapped_column(Float, nullable=True)
    self_report_energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    self_report_recovery: Mapped[float | None] = mapped_column(Float, nullable=True)

    derived: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
