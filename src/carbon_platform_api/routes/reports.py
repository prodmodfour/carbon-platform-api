"""Reporting HTTP routes."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from carbon_platform_api.dependencies import get_reporting_service
from carbon_platform_api.schemas.reports import ReportSummaryResponse
from carbon_platform_api.services.reporting import (
    InvalidReportTimeRangeError,
    ReportingService,
    ReportWorkspaceNotFoundError,
)

router = APIRouter(tags=["reports"])


@router.get("/reports/summary", response_model=ReportSummaryResponse)
async def summarize_all_workspaces(
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    start_time: Annotated[
        datetime | None,
        Query(
            description=(
                "Optional inclusive measured_at lower bound. Must be timezone-aware."
            ),
        ),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(
            description=(
                "Optional exclusive measured_at upper bound. Must be timezone-aware."
            ),
        ),
    ] = None,
) -> ReportSummaryResponse:
    """Return aggregate usage and emissions totals across all workspaces."""
    return await _summarize_usage(
        reporting_service=reporting_service,
        workspace_id=None,
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/workspaces/{workspace_id}/reports/summary",
    response_model=ReportSummaryResponse,
)
async def summarize_workspace(
    workspace_id: UUID,
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    start_time: Annotated[
        datetime | None,
        Query(
            description=(
                "Optional inclusive measured_at lower bound. Must be timezone-aware."
            ),
        ),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(
            description=(
                "Optional exclusive measured_at upper bound. Must be timezone-aware."
            ),
        ),
    ] = None,
) -> ReportSummaryResponse:
    """Return aggregate usage and emissions totals for one workspace."""
    return await _summarize_usage(
        reporting_service=reporting_service,
        workspace_id=workspace_id,
        start_time=start_time,
        end_time=end_time,
    )


async def _summarize_usage(
    *,
    reporting_service: ReportingService,
    workspace_id: UUID | None,
    start_time: datetime | None,
    end_time: datetime | None,
) -> ReportSummaryResponse:
    try:
        summary = await reporting_service.summarize_usage(
            workspace_id=workspace_id,
            start_time=start_time,
            end_time=end_time,
        )
    except ReportWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        ) from exc
    except InvalidReportTimeRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ReportSummaryResponse.model_validate(summary)
