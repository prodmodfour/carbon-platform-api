"""Schemas and value objects for carbon intensity lookups."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CarbonIntensityQuery(BaseModel):
    """Region/time-window lookup for carbon intensity samples."""

    model_config = ConfigDict(frozen=True)

    region: str = Field(
        min_length=1,
        max_length=80,
        examples=["sample-region-1"],
        description="Public-safe region label to query from the provider.",
    )
    start_time: datetime = Field(
        description="Inclusive start of the carbon intensity lookup window."
    )
    end_time: datetime = Field(
        description="Exclusive end of the carbon intensity lookup window."
    )

    @field_validator("region")
    @classmethod
    def strip_and_validate_region(cls, value: str) -> str:
        """Trim region labels and reject whitespace-only values."""
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("region must not be blank")
        return stripped_value

    @field_validator("start_time", "end_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Require timezone-aware lookup windows."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("carbon intensity lookup times must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_time_window(self) -> Self:
        """Require a non-empty forward-moving time window."""
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class CarbonIntensitySample(BaseModel):
    """Carbon intensity sample returned by a provider or cache."""

    model_config = ConfigDict(frozen=True)

    region: str = Field(
        min_length=1,
        max_length=80,
        examples=["sample-region-1"],
        description="Public-safe region label for the measured intensity.",
    )
    measured_at: datetime = Field(
        description="Timezone-aware timestamp for the intensity measurement."
    )
    grams_co2e_per_kwh: Decimal = Field(
        ge=Decimal("0"),
        description="Carbon intensity in grams CO2e per kWh.",
    )
    source: str = Field(
        min_length=1,
        max_length=120,
        examples=["sample-provider"],
        description="Public-safe provider or cache source label.",
    )

    @field_validator("region", "source")
    @classmethod
    def strip_and_validate_text(cls, value: str) -> str:
        """Trim labels and reject whitespace-only values."""
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("carbon intensity text fields must not be blank")
        return stripped_value

    @field_validator("measured_at")
    @classmethod
    def require_measured_at_timezone(cls, value: datetime) -> datetime:
        """Require timezone-aware sample timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at must be timezone-aware")
        return value
