from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import gen_id


class EmployeeBaseline(Base):
    __tablename__ = "employee_baselines"
    __table_args__ = (UniqueConstraint("employee_id", "metric", name="uq_baseline_employee_metric"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String, nullable=False)

    baseline_median: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_mean: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_std: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_mad: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_avg: Mapped[float] = mapped_column(Float, default=0.0)
    trend: Mapped[float] = mapped_column(Float, default=0.0)
    seasonality: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    window_days: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
