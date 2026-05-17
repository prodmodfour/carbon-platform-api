"""Carbon intensity sample persistence model."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from carbon_platform_api.db.base import Base
from carbon_platform_api.models.common import utc_now


class CarbonIntensitySample(Base):
    """A measured grid carbon intensity value for a region and time."""

    __tablename__ = "carbon_intensity_samples"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    region: Mapped[str] = mapped_column(String(length=64), nullable=False, index=True)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    grams_co2e_per_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(length=120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utc_now,
    )
