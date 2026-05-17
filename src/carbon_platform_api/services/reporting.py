"""Reporting business service."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from carbon_platform_api.repositories.reports import ReportQuery, ReportSummaryRecord


class ReportingRepositoryProtocol(Protocol):
    """Reporting persistence operations required by the service."""

    async def summarize(self, query: ReportQuery) -> ReportSummaryRecord:
        """Return aggregate usage and emissions totals for a report query."""
        ...


class WorkspaceLookupRepositoryProtocol(Protocol):
    """Workspace lookup operation required by workspace-scoped reports."""

    async def get(self, workspace_id: UUID) -> object | None:
        """Fetch a workspace by primary key, returning None when missing."""
        ...


class InvalidReportTimeRangeError(ValueError):
    """Raised when a report time range is invalid."""


class ReportWorkspaceNotFoundError(LookupError):
    """Raised when a workspace-scoped report references a missing workspace."""


class ReportingService:
    """Business operations for carbon usage summary reports."""

    def __init__(
        self,
        *,
        report_repository: ReportingRepositoryProtocol,
        workspace_repository: WorkspaceLookupRepositoryProtocol,
    ) -> None:
        """Create a reporting service with small repository abstractions."""
        self._report_repository = report_repository
        self._workspace_repository = workspace_repository

    async def summarize_usage(
        self,
        *,
        workspace_id: UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ReportSummaryRecord:
        """Validate report inputs and return aggregate usage totals."""
        _validate_time_range(start_time=start_time, end_time=end_time)

        if workspace_id is not None:
            workspace = await self._workspace_repository.get(workspace_id)
            if workspace is None:
                raise ReportWorkspaceNotFoundError(str(workspace_id))

        return await self._report_repository.summarize(
            ReportQuery(
                workspace_id=workspace_id,
                start_time=start_time,
                end_time=end_time,
            )
        )


def _validate_time_range(
    *,
    start_time: datetime | None,
    end_time: datetime | None,
) -> None:
    for field_name, value in (
        ("start_time", start_time),
        ("end_time", end_time),
    ):
        if value is None:
            continue
        if value.tzinfo is None or value.utcoffset() is None:
            raise InvalidReportTimeRangeError(f"{field_name} must be timezone-aware.")

    if start_time is not None and end_time is not None and start_time >= end_time:
        raise InvalidReportTimeRangeError("start_time must be before end_time.")
