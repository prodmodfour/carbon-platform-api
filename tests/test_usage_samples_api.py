"""Tests for usage sample ingestion API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from carbon_platform_api.config import Settings
from carbon_platform_api.dependencies import get_usage_ingestion_service
from carbon_platform_api.main import create_app
from carbon_platform_api.repositories.usage_samples import UsageSampleRecord
from carbon_platform_api.schemas.usage_samples import UsageSampleIngestionRequest
from carbon_platform_api.services.usage_ingestion import (
    InvalidUsageSampleError,
    UsageSampleWorkspaceNotFoundError,
)


def default_settings() -> Settings:
    """Return deterministic settings for endpoint tests."""
    return Settings(
        app_name="carbon-platform-api",
        app_version="0.1.0",
        environment="local",
        log_level="INFO",
        docs_enabled=False,
    )


class FakeUsageIngestionService:
    """Fake usage ingestion service for endpoint tests."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[tuple[UUID, UsageSampleIngestionRequest]] = []

    async def ingest_usage_sample(
        self,
        *,
        workspace_id: UUID,
        request: UsageSampleIngestionRequest,
    ) -> UsageSampleRecord:
        """Return a deterministic usage sample or raise a configured error."""
        self.calls.append((workspace_id, request))
        if self._error is not None:
            raise self._error
        return UsageSampleRecord(
            id=uuid4(),
            workspace_id=workspace_id,
            provider=request.provider,
            region=request.region,
            resource_type=request.resource_type.value,
            usage_amount=request.usage_amount,
            usage_unit=request.usage_unit.value,
            measured_at=request.measured_at,
            normalized_usage_amount=Decimal("10.000000"),
            normalized_usage_unit="vcpu_hour",
            energy_kwh=Decimal("0.500000"),
            carbon_intensity_grams_co2e_per_kwh=(
                request.carbon_intensity_grams_co2e_per_kwh
            ),
            estimated_grams_co2e=Decimal("200.0000"),
            factor_source="demo-static-v1",
            created_at=datetime(2026, 1, 1, 12, 1, tzinfo=UTC),
        )


def create_usage_client(service: FakeUsageIngestionService) -> TestClient:
    """Create a test client with the usage service dependency overridden."""
    app = create_app(settings=default_settings())

    def override_get_usage_ingestion_service() -> FakeUsageIngestionService:
        return service

    app.dependency_overrides[get_usage_ingestion_service] = (
        override_get_usage_ingestion_service
    )
    return TestClient(app)


def usage_payload(*, usage_unit: str = "vcpu_hour") -> dict[str, object]:
    """Return a valid JSON payload for usage ingestion."""
    return {
        "provider": " sample-cloud ",
        "region": " sample-region-1 ",
        "resource_type": "vcpu",
        "usage_amount": "10",
        "usage_unit": usage_unit,
        "measured_at": "2026-01-01T12:00:00Z",
        "carbon_intensity_grams_co2e_per_kwh": "400",
    }


def test_usage_ingestion_endpoint_returns_persisted_sample() -> None:
    """The endpoint should delegate ingestion to the service and return its record."""
    service = FakeUsageIngestionService()
    client = create_usage_client(service)
    workspace_id = uuid4()

    response = client.post(
        f"/workspaces/{workspace_id}/usage-samples",
        json=usage_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["workspace_id"] == str(workspace_id)
    assert body["provider"] == "sample-cloud"
    assert body["region"] == "sample-region-1"
    assert body["resource_type"] == "vcpu"
    assert body["usage_unit"] == "vcpu_hour"
    assert body["normalized_usage_unit"] == "vcpu_hour"
    assert Decimal(str(body["usage_amount"])) == Decimal("10")
    assert Decimal(str(body["normalized_usage_amount"])) == Decimal("10.000000")
    assert Decimal(str(body["energy_kwh"])) == Decimal("0.500000")
    assert Decimal(str(body["carbon_intensity_grams_co2e_per_kwh"])) == Decimal("400")
    assert Decimal(str(body["estimated_grams_co2e"])) == Decimal("200.0000")
    assert body["factor_source"] == "demo-static-v1"
    assert len(service.calls) == 1
    called_workspace_id, called_request = service.calls[0]
    assert called_workspace_id == workspace_id
    assert called_request.provider == "sample-cloud"
    assert called_request.region == "sample-region-1"


def test_usage_ingestion_endpoint_returns_missing_workspace_error() -> None:
    """Missing workspaces should return a clear 404 response."""
    client = create_usage_client(
        FakeUsageIngestionService(UsageSampleWorkspaceNotFoundError("missing"))
    )

    response = client.post(
        f"/workspaces/{uuid4()}/usage-samples",
        json=usage_payload(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found."}


def test_usage_ingestion_endpoint_returns_invalid_unit_error() -> None:
    """Incompatible resource/unit pairs should return a clear client error."""
    client = create_usage_client(
        FakeUsageIngestionService(
            InvalidUsageSampleError("Usage unit is not compatible with resource type.")
        )
    )

    response = client.post(
        f"/workspaces/{uuid4()}/usage-samples",
        json=usage_payload(usage_unit="gb"),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Usage unit is not compatible with resource type."
    }
