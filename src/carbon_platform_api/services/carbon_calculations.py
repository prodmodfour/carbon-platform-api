"""Deterministic carbon calculation service using public-safe demo factors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from carbon_platform_api.schemas.carbon_calculations import (
    CarbonCalculationInput,
    CarbonCalculationResult,
    ResourceType,
    UsageUnit,
)

_GRAMS_CO2E_QUANTUM = Decimal("0.0001")
_KWH_QUANTUM = Decimal("0.000001")
_USAGE_QUANTUM = Decimal("0.000001")
_DEMO_FACTOR_SOURCE = "demo-static-v1"


class CarbonCalculationError(ValueError):
    """Base class for carbon calculation failures."""


class InvalidCarbonCalculationInputError(CarbonCalculationError):
    """Raised when calculation inputs fail service-level validation."""


class UnsupportedResourceTypeError(CarbonCalculationError):
    """Raised when no energy factor exists for a resource type."""


class UnsupportedUnitConversionError(CarbonCalculationError):
    """Raised when a usage unit conversion is not supported."""


class IncompatibleUsageUnitError(CarbonCalculationError):
    """Raised when a usage unit is not compatible with the resource type."""


@dataclass(frozen=True, slots=True)
class ResourceEnergyFactor:
    """Energy factor for a resource type using public-safe demo values only."""

    resource_type: ResourceType
    normalized_unit: UsageUnit
    kwh_per_normalized_unit: Decimal
    source: str = _DEMO_FACTOR_SOURCE


class EnergyFactorProviderProtocol(Protocol):
    """Provider interface for resource energy factors."""

    def get_factor(
        self,
        *,
        resource_type: ResourceType,
        region: str,
    ) -> ResourceEnergyFactor:
        """Return the energy factor for the requested resource type and region."""
        ...


class UsageUnitConverterProtocol(Protocol):
    """Provider interface for usage unit conversions."""

    def convert(
        self,
        *,
        amount: Decimal,
        from_unit: UsageUnit,
        to_unit: UsageUnit,
    ) -> Decimal:
        """Convert a usage amount between compatible units."""
        ...


class DemoEnergyFactorProvider:
    """Static public-safe demo energy factors.

    These factors are deliberately simple sample values for deterministic portfolio
    calculations. They are not authoritative emissions or energy measurements.
    """

    _FACTORS: Mapping[ResourceType, ResourceEnergyFactor] = {
        ResourceType.VCPU: ResourceEnergyFactor(
            resource_type=ResourceType.VCPU,
            normalized_unit=UsageUnit.VCPU_HOUR,
            kwh_per_normalized_unit=Decimal("0.0500"),
        ),
        ResourceType.MEMORY: ResourceEnergyFactor(
            resource_type=ResourceType.MEMORY,
            normalized_unit=UsageUnit.GB_HOUR,
            kwh_per_normalized_unit=Decimal("0.0005"),
        ),
        ResourceType.STORAGE: ResourceEnergyFactor(
            resource_type=ResourceType.STORAGE,
            normalized_unit=UsageUnit.GB_MONTH,
            kwh_per_normalized_unit=Decimal("0.0001"),
        ),
        ResourceType.NETWORK: ResourceEnergyFactor(
            resource_type=ResourceType.NETWORK,
            normalized_unit=UsageUnit.GB,
            kwh_per_normalized_unit=Decimal("0.0020"),
        ),
    }

    def get_factor(
        self,
        *,
        resource_type: ResourceType,
        region: str,
    ) -> ResourceEnergyFactor:
        """Return the region-independent demo factor for a resource type."""
        try:
            return self._FACTORS[resource_type]
        except KeyError as exc:
            raise UnsupportedResourceTypeError(
                f"No demo energy factor for resource type: {resource_type!s} "
                f"in region: {region}"
            ) from exc


class DemoUsageUnitConverter:
    """Static unit converter for supported demo calculation units."""

    _CONVERSION_MULTIPLIERS: Mapping[tuple[UsageUnit, UsageUnit], Decimal] = {
        (UsageUnit.VCPU_HOUR, UsageUnit.VCPU_HOUR): Decimal("1"),
        (UsageUnit.VCPU_MINUTE, UsageUnit.VCPU_HOUR): Decimal("1") / Decimal("60"),
        (UsageUnit.GB_HOUR, UsageUnit.GB_HOUR): Decimal("1"),
        (UsageUnit.GB_MINUTE, UsageUnit.GB_HOUR): Decimal("1") / Decimal("60"),
        (UsageUnit.GB_MONTH, UsageUnit.GB_MONTH): Decimal("1"),
        (UsageUnit.TB_MONTH, UsageUnit.GB_MONTH): Decimal("1024"),
        (UsageUnit.GB, UsageUnit.GB): Decimal("1"),
        (UsageUnit.MB, UsageUnit.GB): Decimal("0.0009765625"),
        (UsageUnit.TB, UsageUnit.GB): Decimal("1024"),
    }

    def convert(
        self,
        *,
        amount: Decimal,
        from_unit: UsageUnit,
        to_unit: UsageUnit,
    ) -> Decimal:
        """Convert a usage amount between compatible demo units."""
        try:
            multiplier = self._CONVERSION_MULTIPLIERS[(from_unit, to_unit)]
        except KeyError as exc:
            raise UnsupportedUnitConversionError(
                f"Cannot convert usage from {from_unit!s} to {to_unit!s}."
            ) from exc
        return amount * multiplier


class CarbonCalculationService:
    """Calculate estimated emissions from usage and carbon intensity."""

    def __init__(
        self,
        *,
        energy_factor_provider: EnergyFactorProviderProtocol | None = None,
        unit_converter: UsageUnitConverterProtocol | None = None,
    ) -> None:
        """Create a calculation service with injectable providers."""
        self._energy_factor_provider = (
            energy_factor_provider or DemoEnergyFactorProvider()
        )
        self._unit_converter = unit_converter or DemoUsageUnitConverter()

    def calculate(
        self, calculation_input: CarbonCalculationInput
    ) -> CarbonCalculationResult:
        """Calculate estimated grams CO2e for one usage sample."""
        _validate_input(calculation_input)
        factor = self._energy_factor_provider.get_factor(
            resource_type=calculation_input.resource_type,
            region=calculation_input.region,
        )
        if factor.resource_type != calculation_input.resource_type:
            raise UnsupportedResourceTypeError(
                "Energy factor provider returned a factor for the wrong resource type."
            )

        try:
            normalized_usage_amount = self._unit_converter.convert(
                amount=calculation_input.usage_amount,
                from_unit=calculation_input.usage_unit,
                to_unit=factor.normalized_unit,
            )
        except UnsupportedUnitConversionError as exc:
            raise IncompatibleUsageUnitError(
                f"Usage unit {calculation_input.usage_unit!s} is not compatible with "
                f"resource type {calculation_input.resource_type!s}."
            ) from exc

        energy_kwh = normalized_usage_amount * factor.kwh_per_normalized_unit
        estimated_grams_co2e = (
            energy_kwh * calculation_input.carbon_intensity_grams_co2e_per_kwh
        )

        return CarbonCalculationResult(
            resource_type=calculation_input.resource_type,
            region=calculation_input.region,
            usage_amount=calculation_input.usage_amount,
            usage_unit=calculation_input.usage_unit,
            normalized_usage_amount=_round(normalized_usage_amount, _USAGE_QUANTUM),
            normalized_usage_unit=factor.normalized_unit,
            energy_kwh=_round(energy_kwh, _KWH_QUANTUM),
            carbon_intensity_grams_co2e_per_kwh=(
                calculation_input.carbon_intensity_grams_co2e_per_kwh
            ),
            estimated_grams_co2e=_round(estimated_grams_co2e, _GRAMS_CO2E_QUANTUM),
            factor_source=factor.source,
        )


def _validate_input(calculation_input: CarbonCalculationInput) -> None:
    if calculation_input.usage_amount <= Decimal("0"):
        raise InvalidCarbonCalculationInputError("usage_amount must be positive.")
    if calculation_input.carbon_intensity_grams_co2e_per_kwh < Decimal("0"):
        raise InvalidCarbonCalculationInputError(
            "carbon_intensity_grams_co2e_per_kwh must not be negative."
        )
    if not calculation_input.region.strip():
        raise InvalidCarbonCalculationInputError("region must not be blank.")


def _round(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)
