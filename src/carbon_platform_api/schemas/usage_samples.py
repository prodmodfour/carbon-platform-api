"""Schemas for usage sample ingestion and responses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from carbon_platform_api.schemas.carbon_calculations import ResourceType, UsageUnit


class UsageSampleIngestionRequest(BaseModel):
    """Request body for ingesting one compute usage sample."""

    provider: str = Field(
        min_length=1,
        max_length=64,
        examples=["sample-cloud"],
        description="Public-safe provider label for the usage sample.",
    )
    region: str = Field(
        min_length=1,
        max_length=64,
        examples=["sample-region-1"],
        description="Public-safe region label associated with the usage sample.",
    )
    resource_type: ResourceType = Field(
        description="Demo compute resource category for the usage sample."
    )
    usage_amount: Decimal = Field(
        gt=Decimal("0"),
        max_digits=18,
        decimal_places=6,
        description="Positive usage amount expressed in usage_unit.",
    )
    usage_unit: UsageUnit = Field(description="Unit for usage_amount.")
    measured_at: datetime = Field(
        description="Timezone-aware timestamp for when the usage was measured."
    )
    carbon_intensity_grams_co2e_per_kwh: Decimal = Field(
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=4,
        description=("Carbon intensity in grams CO2e per kWh to use for this sample."),
    )

    @field_validator("provider", "region")
    @classmethod
    def strip_and_validate_text(cls, value: str) -> str:
        """Trim text labels and reject whitespace-only values."""
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("usage sample text fields must not be blank")
        return stripped_value

    @field_validator("measured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Require timezone-aware usage sample timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at must be timezone-aware")
        return value


class UsageSampleResponse(BaseModel):
    """Persisted usage sample returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    provider: str
    region: str
    resource_type: ResourceType
    usage_amount: Decimal
    usage_unit: UsageUnit
    measured_at: datetime
    normalized_usage_amount: Decimal
    normalized_usage_unit: UsageUnit
    energy_kwh: Decimal
    carbon_intensity_grams_co2e_per_kwh: Decimal
    estimated_grams_co2e: Decimal
    factor_source: str
    created_at: datetime
