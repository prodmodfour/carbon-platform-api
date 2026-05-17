"""Schemas and value objects for carbon calculations."""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ResourceType(StrEnum):
    """Supported demo compute resource categories."""

    VCPU = "vcpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"


class UsageUnit(StrEnum):
    """Supported demo usage units for calculation inputs."""

    VCPU_HOUR = "vcpu_hour"
    VCPU_MINUTE = "vcpu_minute"
    GB_HOUR = "gb_hour"
    GB_MINUTE = "gb_minute"
    GB_MONTH = "gb_month"
    TB_MONTH = "tb_month"
    GB = "gb"
    MB = "mb"
    TB = "tb"


class CarbonCalculationInput(BaseModel):
    """Input required to calculate a deterministic carbon estimate."""

    resource_type: ResourceType = Field(
        description="Demo resource category for the usage sample."
    )
    region: str = Field(
        min_length=1,
        max_length=80,
        examples=["sample-region-1"],
        description="Public-safe region label associated with the usage sample.",
    )
    usage_amount: Decimal = Field(
        gt=Decimal("0"),
        description="Positive usage amount expressed in usage_unit.",
    )
    usage_unit: UsageUnit = Field(
        description="Unit for usage_amount. Compatibility is checked by the service."
    )
    carbon_intensity_grams_co2e_per_kwh: Decimal = Field(
        ge=Decimal("0"),
        description=(
            "Carbon intensity in grams CO2e per kWh for the sample region/window."
        ),
    )

    @field_validator("region")
    @classmethod
    def strip_and_validate_region(cls, value: str) -> str:
        """Trim region labels and reject whitespace-only values."""
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("region must not be blank")
        return stripped_value


class CarbonCalculationResult(BaseModel):
    """Deterministic result returned by the carbon calculation service."""

    resource_type: ResourceType
    region: str
    usage_amount: Decimal
    usage_unit: UsageUnit
    normalized_usage_amount: Decimal
    normalized_usage_unit: UsageUnit
    energy_kwh: Decimal
    carbon_intensity_grams_co2e_per_kwh: Decimal
    estimated_grams_co2e: Decimal
    factor_source: str
