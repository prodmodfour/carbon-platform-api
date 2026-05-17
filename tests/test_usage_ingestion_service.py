"""Unit tests for the usage ingestion service."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from carbon_platform_api.repositories.usage_samples import (
    UsageSampleCreate,
    UsageSampleRecord,
)
from carbon_platform_api.schemas.carbon_calculations import ResourceType, UsageUnit
from carbon_platform_api.schemas.usage_samples import UsageSampleIngestionRequest
from carbon_platform_api.services.usage_ingestion import (
    InvalidUsageSampleError,
    UsageIngestionService,
    UsageSampleWorkspaceNotFoundError,
)


class FakeWorkspaceLookupRepository:
    """In-memory workspace lookup for usage ingestion tests."""

    def __init__(self, existing_workspace_ids: set[UUID]) -> None:
        self._existing_workspace_ids = existing_workspace_ids

    async def get(self, workspace_id: UUID) -> object | None:
        """Return an object when the workspace exists."""
        if workspace_id in self._existing_workspace_ids:
            return object()
        return None


class FakeUsageSampleRepository:
    """In-memory usage sample repository for service tests."""

    def __init__(self) -> None:
        self.created_samples: list[UsageSampleCreate] = []

    async def create(self, sample: UsageSampleCreate) -> UsageSampleRecord:
        """Record the sample and return a persisted-looking record."""
        self.created_samples.append(sample)
        return UsageSampleRecord(
            id=uuid4(),
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
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def usage_request(
    *,
    resource_type: ResourceType = ResourceType.VCPU,
    usage_amount: Decimal = Decimal("10"),
    usage_unit: UsageUnit = UsageUnit.VCPU_HOUR,
) -> UsageSampleIngestionRequest:
    """Build a valid usage ingestion request for tests."""
    return UsageSampleIngestionRequest(
        provider=" sample-cloud ",
        region=" sample-region-1 ",
        resource_type=resource_type,
        usage_amount=usage_amount,
        usage_unit=usage_unit,
        measured_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        carbon_intensity_grams_co2e_per_kwh=Decimal("400"),
    )


def test_ingests_usage_sample_with_calculated_estimate() -> None:
    """Usage ingestion should validate, calculate, and persist through repositories."""
    workspace_id = uuid4()
    usage_repository = FakeUsageSampleRepository()
    service = UsageIngestionService(
        workspace_repository=FakeWorkspaceLookupRepository({workspace_id}),
        usage_sample_repository=usage_repository,
    )

    record = asyncio.run(
        service.ingest_usage_sample(
            workspace_id=workspace_id,
            request=usage_request(),
        )
    )

    assert record.workspace_id == workspace_id
    assert record.provider == "sample-cloud"
    assert record.region == "sample-region-1"
    assert record.resource_type == "vcpu"
    assert record.usage_amount == Decimal("10")
    assert record.usage_unit == "vcpu_hour"
    assert record.normalized_usage_amount == Decimal("10.000000")
    assert record.normalized_usage_unit == "vcpu_hour"
    assert record.energy_kwh == Decimal("0.500000")
    assert record.carbon_intensity_grams_co2e_per_kwh == Decimal("400")
    assert record.estimated_grams_co2e == Decimal("200.0000")
    assert record.factor_source == "demo-static-v1"
    assert usage_repository.created_samples == [
        UsageSampleCreate(
            workspace_id=workspace_id,
            provider="sample-cloud",
            region="sample-region-1",
            resource_type="vcpu",
            usage_amount=Decimal("10"),
            usage_unit="vcpu_hour",
            measured_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            normalized_usage_amount=Decimal("10.000000"),
            normalized_usage_unit="vcpu_hour",
            energy_kwh=Decimal("0.500000"),
            carbon_intensity_grams_co2e_per_kwh=Decimal("400"),
            estimated_grams_co2e=Decimal("200.0000"),
            factor_source="demo-static-v1",
        )
    ]


def test_ingestion_rejects_missing_workspace_before_persistence() -> None:
    """Usage ingestion should fail clearly when the workspace does not exist."""
    usage_repository = FakeUsageSampleRepository()
    service = UsageIngestionService(
        workspace_repository=FakeWorkspaceLookupRepository(set()),
        usage_sample_repository=usage_repository,
    )

    with pytest.raises(UsageSampleWorkspaceNotFoundError):
        asyncio.run(
            service.ingest_usage_sample(
                workspace_id=uuid4(),
                request=usage_request(),
            )
        )

    assert usage_repository.created_samples == []


def test_ingestion_rejects_incompatible_usage_units_before_persistence() -> None:
    """Usage ingestion should reject units incompatible with the resource type."""
    workspace_id = uuid4()
    usage_repository = FakeUsageSampleRepository()
    service = UsageIngestionService(
        workspace_repository=FakeWorkspaceLookupRepository({workspace_id}),
        usage_sample_repository=usage_repository,
    )

    with pytest.raises(InvalidUsageSampleError, match="Usage unit"):
        asyncio.run(
            service.ingest_usage_sample(
                workspace_id=workspace_id,
                request=usage_request(usage_unit=UsageUnit.GB),
            )
        )

    assert usage_repository.created_samples == []
