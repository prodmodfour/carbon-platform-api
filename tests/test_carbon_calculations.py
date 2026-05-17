"""Unit tests for deterministic carbon calculations."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from carbon_platform_api.schemas.carbon_calculations import (
    CarbonCalculationInput,
    ResourceType,
    UsageUnit,
)
from carbon_platform_api.services.carbon_calculations import (
    CarbonCalculationService,
    IncompatibleUsageUnitError,
    ResourceEnergyFactor,
)


def calculation_input(
    *,
    resource_type: ResourceType,
    usage_amount: Decimal,
    usage_unit: UsageUnit,
    carbon_intensity: Decimal = Decimal("400"),
) -> CarbonCalculationInput:
    """Build a valid calculation input with a public-safe sample region."""
    return CarbonCalculationInput(
        resource_type=resource_type,
        region=" sample-region-1 ",
        usage_amount=usage_amount,
        usage_unit=usage_unit,
        carbon_intensity_grams_co2e_per_kwh=carbon_intensity,
    )


@pytest.mark.parametrize(
    (
        "resource_type",
        "usage_amount",
        "usage_unit",
        "expected_normalized_amount",
        "expected_normalized_unit",
        "expected_kwh",
        "expected_grams_co2e",
    ),
    [
        (
            ResourceType.VCPU,
            Decimal("10"),
            UsageUnit.VCPU_HOUR,
            Decimal("10.000000"),
            UsageUnit.VCPU_HOUR,
            Decimal("0.500000"),
            Decimal("200.0000"),
        ),
        (
            ResourceType.MEMORY,
            Decimal("100"),
            UsageUnit.GB_HOUR,
            Decimal("100.000000"),
            UsageUnit.GB_HOUR,
            Decimal("0.050000"),
            Decimal("20.0000"),
        ),
        (
            ResourceType.STORAGE,
            Decimal("1000"),
            UsageUnit.GB_MONTH,
            Decimal("1000.000000"),
            UsageUnit.GB_MONTH,
            Decimal("0.100000"),
            Decimal("40.0000"),
        ),
        (
            ResourceType.NETWORK,
            Decimal("50"),
            UsageUnit.GB,
            Decimal("50.000000"),
            UsageUnit.GB,
            Decimal("0.100000"),
            Decimal("40.0000"),
        ),
    ],
)
def test_calculates_emissions_for_supported_resource_types(
    resource_type: ResourceType,
    usage_amount: Decimal,
    usage_unit: UsageUnit,
    expected_normalized_amount: Decimal,
    expected_normalized_unit: UsageUnit,
    expected_kwh: Decimal,
    expected_grams_co2e: Decimal,
) -> None:
    """Supported resource types should use deterministic demo factors."""
    service = CarbonCalculationService()

    result = service.calculate(
        calculation_input(
            resource_type=resource_type,
            usage_amount=usage_amount,
            usage_unit=usage_unit,
        )
    )

    assert result.resource_type == resource_type
    assert result.region == "sample-region-1"
    assert result.normalized_usage_amount == expected_normalized_amount
    assert result.normalized_usage_unit == expected_normalized_unit
    assert result.energy_kwh == expected_kwh
    assert result.estimated_grams_co2e == expected_grams_co2e
    assert result.factor_source == "demo-static-v1"


@pytest.mark.parametrize(
    (
        "resource_type",
        "usage_amount",
        "usage_unit",
        "carbon_intensity",
        "expected_normalized_amount",
        "expected_normalized_unit",
        "expected_kwh",
        "expected_grams_co2e",
    ),
    [
        (
            ResourceType.VCPU,
            Decimal("120"),
            UsageUnit.VCPU_MINUTE,
            Decimal("100"),
            Decimal("2.000000"),
            UsageUnit.VCPU_HOUR,
            Decimal("0.100000"),
            Decimal("10.0000"),
        ),
        (
            ResourceType.MEMORY,
            Decimal("120"),
            UsageUnit.GB_MINUTE,
            Decimal("1000"),
            Decimal("2.000000"),
            UsageUnit.GB_HOUR,
            Decimal("0.001000"),
            Decimal("1.0000"),
        ),
        (
            ResourceType.STORAGE,
            Decimal("2"),
            UsageUnit.TB_MONTH,
            Decimal("100"),
            Decimal("2048.000000"),
            UsageUnit.GB_MONTH,
            Decimal("0.204800"),
            Decimal("20.4800"),
        ),
        (
            ResourceType.NETWORK,
            Decimal("512"),
            UsageUnit.MB,
            Decimal("1000"),
            Decimal("0.500000"),
            UsageUnit.GB,
            Decimal("0.001000"),
            Decimal("1.0000"),
        ),
    ],
)
def test_converts_supported_usage_units_before_calculation(
    resource_type: ResourceType,
    usage_amount: Decimal,
    usage_unit: UsageUnit,
    carbon_intensity: Decimal,
    expected_normalized_amount: Decimal,
    expected_normalized_unit: UsageUnit,
    expected_kwh: Decimal,
    expected_grams_co2e: Decimal,
) -> None:
    """Usage units should be converted to the resource factor's normalized unit."""
    service = CarbonCalculationService()

    result = service.calculate(
        calculation_input(
            resource_type=resource_type,
            usage_amount=usage_amount,
            usage_unit=usage_unit,
            carbon_intensity=carbon_intensity,
        )
    )

    assert result.normalized_usage_amount == expected_normalized_amount
    assert result.normalized_usage_unit == expected_normalized_unit
    assert result.energy_kwh == expected_kwh
    assert result.estimated_grams_co2e == expected_grams_co2e


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("usage_amount", Decimal("0")),
        ("usage_amount", Decimal("-1")),
        ("carbon_intensity_grams_co2e_per_kwh", Decimal("-0.01")),
        ("region", "   "),
        ("resource_type", "gpu"),
    ],
)
def test_calculation_input_rejects_invalid_values(
    field_name: str,
    value: object,
) -> None:
    """Calculation inputs should reject invalid values before service use."""
    payload: dict[str, object] = {
        "resource_type": ResourceType.VCPU,
        "region": "sample-region-1",
        "usage_amount": Decimal("1"),
        "usage_unit": UsageUnit.VCPU_HOUR,
        "carbon_intensity_grams_co2e_per_kwh": Decimal("100"),
    }
    payload[field_name] = value

    with pytest.raises(ValidationError):
        CarbonCalculationInput.model_validate(payload)


def test_rejects_incompatible_usage_unit_for_resource_type() -> None:
    """The service should reject units that cannot be used for a resource type."""
    service = CarbonCalculationService()
    invalid_input = calculation_input(
        resource_type=ResourceType.VCPU,
        usage_amount=Decimal("1"),
        usage_unit=UsageUnit.GB,
    )

    with pytest.raises(IncompatibleUsageUnitError, match="vcpu"):
        service.calculate(invalid_input)


def test_rounds_energy_and_estimated_grams_deterministically() -> None:
    """Energy and emissions outputs should use deterministic Decimal rounding."""
    service = CarbonCalculationService()

    result = service.calculate(
        calculation_input(
            resource_type=ResourceType.VCPU,
            usage_amount=Decimal("1"),
            usage_unit=UsageUnit.VCPU_HOUR,
            carbon_intensity=Decimal("333.3333"),
        )
    )

    assert result.energy_kwh == Decimal("0.050000")
    assert result.estimated_grams_co2e == Decimal("16.6667")


class FakeEnergyFactorProvider:
    """Test provider that demonstrates service extensibility."""

    def get_factor(
        self,
        *,
        resource_type: ResourceType,
        region: str,
    ) -> ResourceEnergyFactor:
        """Return a replacement factor without changing service logic."""
        assert region == "sample-region-1"
        return ResourceEnergyFactor(
            resource_type=resource_type,
            normalized_unit=UsageUnit.VCPU_HOUR,
            kwh_per_normalized_unit=Decimal("0.1000"),
            source="test-provider",
        )


def test_custom_factor_provider_can_be_injected() -> None:
    """Calculation factor providers should be replaceable through the protocol."""
    service = CarbonCalculationService(
        energy_factor_provider=FakeEnergyFactorProvider()
    )

    result = service.calculate(
        calculation_input(
            resource_type=ResourceType.VCPU,
            usage_amount=Decimal("2"),
            usage_unit=UsageUnit.VCPU_HOUR,
            carbon_intensity=Decimal("100"),
        )
    )

    assert result.energy_kwh == Decimal("0.200000")
    assert result.estimated_grams_co2e == Decimal("20.0000")
    assert result.factor_source == "test-provider"
