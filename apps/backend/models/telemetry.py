from datetime import date as date_type

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id


class TelemetryEvent(Base, TimestampMixin):
    __tablename__ = "telemetry_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="desktop_agent")


class SelfReport(Base, TimestampMixin):
    __tablename__ = "self_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    stress: Mapped[int] = mapped_column(Integer, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, nullable=False)
    recovery: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
