"""Usage sample repository backed by SQLAlchemy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from carbon_platform_api.models.usage_sample import UsageSample


@dataclass(frozen=True, slots=True)
class UsageSampleCreate:
    """Repository-level data required to persist one usage sample."""

    workspace_id: UUID
    provider: str
    region: str
    resource_type: str
    usage_amount: Decimal
    usage_unit: str
    measured_at: datetime
    normalized_usage_amount: Decimal
    normalized_usage_unit: str
    energy_kwh: Decimal
    carbon_intensity_grams_co2e_per_kwh: Decimal
    estimated_grams_co2e: Decimal
    factor_source: str


@dataclass(frozen=True, slots=True)
class UsageSampleRecord:
    """Repository-level usage sample data returned to services."""

    id: UUID
    workspace_id: UUID
    provider: str
    region: str
    resource_type: str
    usage_amount: Decimal
    usage_unit: str
    measured_at: datetime
    normalized_usage_amount: Decimal
    normalized_usage_unit: str
    energy_kwh: Decimal
    carbon_intensity_grams_co2e_per_kwh: Decimal
    estimated_grams_co2e: Decimal
    factor_source: str
    created_at: datetime


class UsageSampleRepository:
    """Persistence operations for usage samples."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a repository using an externally managed session."""
        self._session = session

    async def create(self, sample: UsageSampleCreate) -> UsageSampleRecord:
        """Create a usage sample and flush it to the current transaction."""
        usage_sample = UsageSample(
            workspace_id=sample.workspace_id,
            provider=sample.provider,
            region=sample.region,
            resource_type=sample.resource_type,
            usage_amount=sample.usage_amount,
            usage_unit=sample.usage_unit,
            measured_at=sample.measured_at,
            normalized_usage_amount=sample.normalized_usage_amount,
            normalized_usage_unit=sample.normalized_usage_unit,
            energy_kwh=sample.energy_kwh,
            carbon_intensity_grams_co2e_per_kwh=(
                sample.carbon_intensity_grams_co2e_per_kwh
            ),
            estimated_grams_co2e=sample.estimated_grams_co2e,
            factor_source=sample.factor_source,
        )
        self._session.add(usage_sample)
        await self._session.flush()
        await self._session.refresh(usage_sample)
        return _to_record(usage_sample)


def _to_record(usage_sample: UsageSample) -> UsageSampleRecord:
    return UsageSampleRecord(
        id=usage_sample.id,
        workspace_id=usage_sample.workspace_id,
        provider=usage_sample.provider,
        region=usage_sample.region,
        resource_type=usage_sample.resource_type,
        usage_amount=usage_sample.usage_amount,
        usage_unit=usage_sample.usage_unit,
        measured_at=usage_sample.measured_at,
        normalized_usage_amount=usage_sample.normalized_usage_amount,
        normalized_usage_unit=usage_sample.normalized_usage_unit,
        energy_kwh=usage_sample.energy_kwh,
        carbon_intensity_grams_co2e_per_kwh=(
            usage_sample.carbon_intensity_grams_co2e_per_kwh
        ),
        estimated_grams_co2e=usage_sample.estimated_grams_co2e,
        factor_source=usage_sample.factor_source,
        created_at=usage_sample.created_at,
    )
