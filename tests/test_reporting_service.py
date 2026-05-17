"""Unit tests for the reporting service."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from carbon_platform_api.repositories.reports import (
    ReportQuery,
    ReportSummaryRecord,
    ReportTimeRangeRecord,
    ReportTotalsRecord,
)
from carbon_platform_api.services.reporting import (
    InvalidReportTimeRangeError,
    ReportingService,
    ReportWorkspaceNotFoundError,
)


class FakeReportingRepository:
    """In-memory reporting repository for service tests."""

    def __init__(self) -> None:
        self.queries: list[ReportQuery] = []

    async def summarize(self, query: ReportQuery) -> ReportSummaryRecord:
        """Record the query and return an empty summary."""
        self.queries.append(query)
        return ReportSummaryRecord(
            time_range=ReportTimeRangeRecord(
                start_time=query.start_time,
                end_time=query.end_time,
            ),
            total=ReportTotalsRecord(
                usage_sample_count=0,
                energy_kwh=Decimal("0.000000"),
                estimated_grams_co2e=Decimal("0.0000"),
            ),
            by_workspace=[],
            by_provider=[],
            by_region=[],
        )


class FakeWorkspaceLookupRepository:
    """In-memory workspace lookup for service tests."""

    def __init__(self, existing_workspace_ids: set[UUID]) -> None:
        self._existing_workspace_ids = existing_workspace_ids

    async def get(self, workspace_id: UUID) -> object | None:
        """Return an object when the workspace exists."""
        if workspace_id in self._existing_workspace_ids:
            return object()
        return None


def test_reporting_service_validates_and_forwards_report_filters() -> None:
    """Reporting should validate inputs and delegate aggregation to the repository."""
    workspace_id = uuid4()
    reporting_repository = FakeReportingRepository()
    service = ReportingService(
        report_repository=reporting_repository,
        workspace_repository=FakeWorkspaceLookupRepository({workspace_id}),
    )
    start_time = datetime(2026, 1, 1, tzinfo=UTC)
    end_time = datetime(2026, 2, 1, tzinfo=UTC)

    summary = asyncio.run(
        service.summarize_usage(
            workspace_id=workspace_id,
            start_time=start_time,
            end_time=end_time,
        )
    )

    assert summary.total.usage_sample_count == 0
    assert reporting_repository.queries == [
        ReportQuery(
            workspace_id=workspace_id,
            start_time=start_time,
            end_time=end_time,
        )
    ]


def test_reporting_service_rejects_invalid_time_range_before_querying() -> None:
    """The service should reject ranges where start_time is not before end_time."""
    reporting_repository = FakeReportingRepository()
    service = ReportingService(
        report_repository=reporting_repository,
        workspace_repository=FakeWorkspaceLookupRepository(set()),
    )

    with pytest.raises(InvalidReportTimeRangeError, match="start_time"):
        asyncio.run(
            service.summarize_usage(
                start_time=datetime(2026, 2, 1, tzinfo=UTC),
                end_time=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

    assert reporting_repository.queries == []


def test_reporting_service_requires_timezone_aware_filters() -> None:
    """Report timestamps should be timezone-aware to avoid ambiguous filtering."""
    service = ReportingService(
        report_repository=FakeReportingRepository(),
        workspace_repository=FakeWorkspaceLookupRepository(set()),
    )

    with pytest.raises(InvalidReportTimeRangeError, match="start_time"):
        asyncio.run(service.summarize_usage(start_time=datetime(2026, 1, 1)))


def test_workspace_report_rejects_missing_workspace_before_querying() -> None:
    """Workspace-scoped reports should fail clearly when the workspace is missing."""
    reporting_repository = FakeReportingRepository()
    service = ReportingService(
        report_repository=reporting_repository,
        workspace_repository=FakeWorkspaceLookupRepository(set()),
    )

    with pytest.raises(ReportWorkspaceNotFoundError):
        asyncio.run(service.summarize_usage(workspace_id=uuid4()))

    assert reporting_repository.queries == []
