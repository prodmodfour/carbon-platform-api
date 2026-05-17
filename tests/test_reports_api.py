"""Tests for reporting API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from carbon_platform_api.config import Settings
from carbon_platform_api.dependencies import get_reporting_service
from carbon_platform_api.main import create_app
from carbon_platform_api.repositories.reports import (
    ProviderReportGroupRecord,
    RegionReportGroupRecord,
    ReportSummaryRecord,
    ReportTimeRangeRecord,
    ReportTotalsRecord,
    WorkspaceReportGroupRecord,
)
from carbon_platform_api.services.reporting import (
    InvalidReportTimeRangeError,
    ReportWorkspaceNotFoundError,
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


class FakeReportingService:
    """Fake reporting service for endpoint tests."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[tuple[UUID | None, datetime | None, datetime | None]] = []

    async def summarize_usage(
        self,
        *,
        workspace_id: UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ReportSummaryRecord:
        """Return a deterministic summary or raise a configured error."""
        self.calls.append((workspace_id, start_time, end_time))
        if self._error is not None:
            raise self._error

        report_workspace_id = workspace_id or uuid4()
        return ReportSummaryRecord(
            time_range=ReportTimeRangeRecord(
                start_time=start_time,
                end_time=end_time,
            ),
            total=ReportTotalsRecord(
                usage_sample_count=2,
                energy_kwh=Decimal("0.750000"),
                estimated_grams_co2e=Decimal("300.0000"),
            ),
            by_workspace=[
                WorkspaceReportGroupRecord(
                    workspace_id=report_workspace_id,
                    workspace_name="Demo Workspace",
                    usage_sample_count=2,
                    energy_kwh=Decimal("0.750000"),
                    estimated_grams_co2e=Decimal("300.0000"),
                )
            ],
            by_provider=[
                ProviderReportGroupRecord(
                    provider="sample-cloud",
                    usage_sample_count=2,
                    energy_kwh=Decimal("0.750000"),
                    estimated_grams_co2e=Decimal("300.0000"),
                )
            ],
            by_region=[
                RegionReportGroupRecord(
                    region="sample-region-1",
                    usage_sample_count=2,
                    energy_kwh=Decimal("0.750000"),
                    estimated_grams_co2e=Decimal("300.0000"),
                )
            ],
        )


def create_reporting_client(service: FakeReportingService) -> TestClient:
    """Create a test client with the reporting service dependency overridden."""
    app = create_app(settings=default_settings())

    def override_get_reporting_service() -> FakeReportingService:
        return service

    app.dependency_overrides[get_reporting_service] = override_get_reporting_service
    return TestClient(app)


def test_global_report_endpoint_returns_summary_with_filters() -> None:
    """The global report endpoint should delegate filters and return summary groups."""
    service = FakeReportingService()
    client = create_reporting_client(service)

    response = client.get(
        "/reports/summary",
        params={
            "start_time": "2026-01-01T00:00:00Z",
            "end_time": "2026-02-01T00:00:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["time_range"] == {
        "start_time": "2026-01-01T00:00:00Z",
        "end_time": "2026-02-01T00:00:00Z",
    }
    assert body["total"] == {
        "usage_sample_count": 2,
        "energy_kwh": "0.750000",
        "estimated_grams_co2e": "300.0000",
    }
    assert body["by_workspace"][0]["workspace_name"] == "Demo Workspace"
    assert body["by_provider"] == [
        {
            "provider": "sample-cloud",
            "usage_sample_count": 2,
            "energy_kwh": "0.750000",
            "estimated_grams_co2e": "300.0000",
        }
    ]
    assert body["by_region"][0]["region"] == "sample-region-1"
    assert service.calls == [
        (
            None,
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
        )
    ]


def test_workspace_report_endpoint_returns_workspace_summary() -> None:
    """The workspace report endpoint should pass the workspace ID to the service."""
    service = FakeReportingService()
    client = create_reporting_client(service)
    workspace_id = uuid4()

    response = client.get(f"/workspaces/{workspace_id}/reports/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["by_workspace"][0]["workspace_id"] == str(workspace_id)
    assert service.calls == [(workspace_id, None, None)]


def test_report_endpoint_returns_clear_invalid_range_error() -> None:
    """Invalid report ranges should return a clear 422 response."""
    client = create_reporting_client(
        FakeReportingService(
            InvalidReportTimeRangeError("start_time must be before end_time.")
        )
    )

    response = client.get("/reports/summary")

    assert response.status_code == 422
    assert response.json() == {"detail": "start_time must be before end_time."}


def test_workspace_report_endpoint_returns_missing_workspace_error() -> None:
    """Missing workspace-scoped reports should return a clear 404 response."""
    client = create_reporting_client(
        FakeReportingService(ReportWorkspaceNotFoundError("missing"))
    )

    response = client.get(f"/workspaces/{uuid4()}/reports/summary")

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found."}
