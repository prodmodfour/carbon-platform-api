"""Schemas for carbon usage summary reports."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportTimeRangeResponse(BaseModel):
    """Time bounds applied to a summary report."""

    model_config = ConfigDict(from_attributes=True)

    start_time: datetime | None = Field(
        default=None,
        description="Inclusive lower measured_at bound applied to the report.",
    )
    end_time: datetime | None = Field(
        default=None,
        description="Exclusive upper measured_at bound applied to the report.",
    )


class ReportTotalsResponse(BaseModel):
    """Aggregate report totals."""

    model_config = ConfigDict(from_attributes=True)

    usage_sample_count: int = Field(ge=0)
    energy_kwh: Decimal = Field(
        ge=Decimal("0"),
        description="Total calculated demo energy use in kWh.",
    )
    estimated_grams_co2e: Decimal = Field(
        ge=Decimal("0"),
        description="Total calculated demo emissions estimate in grams CO2e.",
    )


class WorkspaceReportGroupResponse(ReportTotalsResponse):
    """Totals grouped by workspace."""

    workspace_id: UUID
    workspace_name: str


class ProviderReportGroupResponse(ReportTotalsResponse):
    """Totals grouped by provider label."""

    provider: str


class RegionReportGroupResponse(ReportTotalsResponse):
    """Totals grouped by region label."""

    region: str


class ReportSummaryResponse(BaseModel):
    """Summary report response grouped by common dimensions."""

    model_config = ConfigDict(from_attributes=True)

    time_range: ReportTimeRangeResponse
    total: ReportTotalsResponse
    by_workspace: list[WorkspaceReportGroupResponse]
    by_provider: list[ProviderReportGroupResponse]
    by_region: list[RegionReportGroupResponse]
