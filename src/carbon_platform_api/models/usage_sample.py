"""Compute usage sample persistence model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from carbon_platform_api.db.base import Base
from carbon_platform_api.models.common import utc_now


class UsageSample(Base):
    """A raw compute usage measurement belonging to a workspace."""

    __tablename__ = "usage_samples"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(length=64), nullable=False)
    region: Mapped[str] = mapped_column(String(length=64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(length=64), nullable=False)
    usage_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    usage_unit: Mapped[str] = mapped_column(String(length=32), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    normalized_usage_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )
    normalized_usage_unit: Mapped[str] = mapped_column(
        String(length=32),
        nullable=False,
    )
    energy_kwh: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    carbon_intensity_grams_co2e_per_kwh: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    estimated_grams_co2e: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )
    factor_source: Mapped[str] = mapped_column(String(length=120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utc_now,
    )
