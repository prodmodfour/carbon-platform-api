"""Reporting repository backed by SQLAlchemy aggregate queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from carbon_platform_api.models.usage_sample import UsageSample
from carbon_platform_api.models.workspace import Workspace

_ENERGY_QUANTUM = Decimal("0.000001")
_GRAMS_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class ReportQuery:
    """Repository-level report filters."""

    workspace_id: UUID | None
    start_time: datetime | None
    end_time: datetime | None


@dataclass(frozen=True, slots=True)
class ReportTimeRangeRecord:
    """Time bounds applied to a report."""

    start_time: datetime | None
    end_time: datetime | None


@dataclass(frozen=True, slots=True)
class ReportTotalsRecord:
    """Aggregated report totals."""

    usage_sample_count: int
    energy_kwh: Decimal
    estimated_grams_co2e: Decimal


@dataclass(frozen=True, slots=True)
class WorkspaceReportGroupRecord:
    """Aggregated totals for one workspace."""

    workspace_id: UUID
    workspace_name: str
    usage_sample_count: int
    energy_kwh: Decimal
    estimated_grams_co2e: Decimal


@dataclass(frozen=True, slots=True)
class ProviderReportGroupRecord:
    """Aggregated totals for one provider label."""

    provider: str
    usage_sample_count: int
    energy_kwh: Decimal
    estimated_grams_co2e: Decimal


@dataclass(frozen=True, slots=True)
class RegionReportGroupRecord:
    """Aggregated totals for one region label."""

    region: str
    usage_sample_count: int
    energy_kwh: Decimal
    estimated_grams_co2e: Decimal


@dataclass(frozen=True, slots=True)
class ReportSummaryRecord:
    """Complete summary report returned by the repository."""

    time_range: ReportTimeRangeRecord
    total: ReportTotalsRecord
    by_workspace: list[WorkspaceReportGroupRecord]
    by_provider: list[ProviderReportGroupRecord]
    by_region: list[RegionReportGroupRecord]


class ReportingRepository:
    """Read-only reporting queries for persisted usage samples."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a reporting repository using an externally managed session."""
        self._session = session

    async def summarize(self, query: ReportQuery) -> ReportSummaryRecord:
        """Return aggregate usage and emissions totals for the requested filters."""
        return ReportSummaryRecord(
            time_range=ReportTimeRangeRecord(
                start_time=query.start_time,
                end_time=query.end_time,
            ),
            total=await self._fetch_total(query),
            by_workspace=await self._fetch_by_workspace(query),
            by_provider=await self._fetch_by_provider(query),
            by_region=await self._fetch_by_region(query),
        )

    async def _fetch_total(self, query: ReportQuery) -> ReportTotalsRecord:
        statement = _apply_usage_filters(
            select(
                func.count(UsageSample.id).label("usage_sample_count"),
                func.coalesce(func.sum(UsageSample.energy_kwh), Decimal("0")).label(
                    "energy_kwh"
                ),
                func.coalesce(
                    func.sum(UsageSample.estimated_grams_co2e),
                    Decimal("0"),
                ).label("estimated_grams_co2e"),
            ),
            query,
        )
        row = (await self._session.execute(statement)).mappings().one()
        return ReportTotalsRecord(
            usage_sample_count=int(row["usage_sample_count"]),
            energy_kwh=_quantize_decimal(row["energy_kwh"], _ENERGY_QUANTUM),
            estimated_grams_co2e=_quantize_decimal(
                row["estimated_grams_co2e"],
                _GRAMS_QUANTUM,
            ),
        )

    async def _fetch_by_workspace(
        self,
        query: ReportQuery,
    ) -> list[WorkspaceReportGroupRecord]:
        statement = _apply_usage_filters(
            select(
                Workspace.id.label("workspace_id"),
                Workspace.name.label("workspace_name"),
                func.count(UsageSample.id).label("usage_sample_count"),
                func.coalesce(func.sum(UsageSample.energy_kwh), Decimal("0")).label(
                    "energy_kwh"
                ),
                func.coalesce(
                    func.sum(UsageSample.estimated_grams_co2e),
                    Decimal("0"),
                ).label("estimated_grams_co2e"),
            )
            .join(UsageSample, UsageSample.workspace_id == Workspace.id)
            .group_by(Workspace.id, Workspace.name)
            .order_by(Workspace.name, Workspace.id),
            query,
        )
        rows = (await self._session.execute(statement)).mappings().all()
        return [
            WorkspaceReportGroupRecord(
                workspace_id=cast(UUID, row["workspace_id"]),
                workspace_name=str(row["workspace_name"]),
                usage_sample_count=int(row["usage_sample_count"]),
                energy_kwh=_quantize_decimal(row["energy_kwh"], _ENERGY_QUANTUM),
                estimated_grams_co2e=_quantize_decimal(
                    row["estimated_grams_co2e"],
                    _GRAMS_QUANTUM,
                ),
            )
            for row in rows
        ]

    async def _fetch_by_provider(
        self,
        query: ReportQuery,
    ) -> list[ProviderReportGroupRecord]:
        statement = _apply_usage_filters(
            select(
                UsageSample.provider.label("provider"),
                func.count(UsageSample.id).label("usage_sample_count"),
                func.coalesce(func.sum(UsageSample.energy_kwh), Decimal("0")).label(
                    "energy_kwh"
                ),
                func.coalesce(
                    func.sum(UsageSample.estimated_grams_co2e),
                    Decimal("0"),
                ).label("estimated_grams_co2e"),
            )
            .group_by(UsageSample.provider)
            .order_by(UsageSample.provider),
            query,
        )
        rows = (await self._session.execute(statement)).mappings().all()
        return [
            ProviderReportGroupRecord(
                provider=str(row["provider"]),
                usage_sample_count=int(row["usage_sample_count"]),
                energy_kwh=_quantize_decimal(row["energy_kwh"], _ENERGY_QUANTUM),
                estimated_grams_co2e=_quantize_decimal(
                    row["estimated_grams_co2e"],
                    _GRAMS_QUANTUM,
                ),
            )
            for row in rows
        ]

    async def _fetch_by_region(
        self,
        query: ReportQuery,
    ) -> list[RegionReportGroupRecord]:
        statement = _apply_usage_filters(
            select(
                UsageSample.region.label("region"),
                func.count(UsageSample.id).label("usage_sample_count"),
                func.coalesce(func.sum(UsageSample.energy_kwh), Decimal("0")).label(
                    "energy_kwh"
                ),
                func.coalesce(
                    func.sum(UsageSample.estimated_grams_co2e),
                    Decimal("0"),
                ).label("estimated_grams_co2e"),
            )
            .group_by(UsageSample.region)
            .order_by(UsageSample.region),
            query,
        )
        rows = (await self._session.execute(statement)).mappings().all()
        return [
            RegionReportGroupRecord(
                region=str(row["region"]),
                usage_sample_count=int(row["usage_sample_count"]),
                energy_kwh=_quantize_decimal(row["energy_kwh"], _ENERGY_QUANTUM),
                estimated_grams_co2e=_quantize_decimal(
                    row["estimated_grams_co2e"],
                    _GRAMS_QUANTUM,
                ),
            )
            for row in rows
        ]


def _apply_usage_filters(
    statement: Select[tuple[Any, ...]], query: ReportQuery
) -> Select[tuple[Any, ...]]:
    if query.workspace_id is not None:
        statement = statement.where(UsageSample.workspace_id == query.workspace_id)
    if query.start_time is not None:
        statement = statement.where(UsageSample.measured_at >= query.start_time)
    if query.end_time is not None:
        statement = statement.where(UsageSample.measured_at < query.end_time)
    return statement


def _quantize_decimal(value: object, quantum: Decimal) -> Decimal:
    if value is None:
        return Decimal("0").quantize(quantum)
    if isinstance(value, Decimal):
        return value.quantize(quantum)
    return Decimal(str(value)).quantize(quantum)
