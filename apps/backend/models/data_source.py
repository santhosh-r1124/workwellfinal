from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import gen_id


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    collectible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
