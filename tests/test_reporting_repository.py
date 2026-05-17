"""Integration tests for reporting persistence queries using PostgreSQL."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from carbon_platform_api.db.base import Base
from carbon_platform_api.db.session import (
    create_database_engine,
    create_session_factory,
)
from carbon_platform_api.repositories.reports import ReportingRepository, ReportQuery
from carbon_platform_api.repositories.usage_samples import (
    UsageSampleCreate,
    UsageSampleRepository,
)
from carbon_platform_api.repositories.workspaces import WorkspaceRepository

_DEFAULT_ADMIN_DATABASE_URL = (
    "postgresql+asyncpg://carbon_platform_api:local_dev_password"
    "@localhost:5432/postgres"
)
_DATABASE_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@pytest.fixture()
def postgres_database_url() -> Iterator[str]:
    """Create an isolated PostgreSQL database for a repository test."""
    admin_url = make_url(
        os.environ.get(
            "CARBON_API_TEST_DATABASE_ADMIN_URL",
            _DEFAULT_ADMIN_DATABASE_URL,
        )
    )
    database_name = f"carbon_platform_api_test_{uuid4().hex}"

    asyncio.run(_create_database(admin_url, database_name))
    try:
        database_url = admin_url.set(database=database_name)
        yield database_url.render_as_string(hide_password=False)
    finally:
        asyncio.run(_drop_database(admin_url, database_name))


def test_reporting_repository_returns_empty_summary(
    postgres_database_url: str,
) -> None:
    """Reporting queries should return deterministic zero totals with no samples."""
    asyncio.run(_exercise_empty_reporting_repository(postgres_database_url))


def test_reporting_repository_aggregates_and_filters_usage_samples(
    postgres_database_url: str,
) -> None:
    """Reporting queries should aggregate usage samples by supported dimensions."""
    asyncio.run(_exercise_aggregated_reporting_repository(postgres_database_url))


async def _exercise_empty_reporting_repository(database_url: str) -> None:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            repository = ReportingRepository(session)
            summary = await repository.summarize(
                ReportQuery(workspace_id=None, start_time=None, end_time=None)
            )

        assert summary.total.usage_sample_count == 0
        assert summary.total.energy_kwh == Decimal("0.000000")
        assert summary.total.estimated_grams_co2e == Decimal("0.0000")
        assert summary.by_workspace == []
        assert summary.by_provider == []
        assert summary.by_region == []
    finally:
        await engine.dispose()


async def _exercise_aggregated_reporting_repository(database_url: str) -> None:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            workspace_repository = WorkspaceRepository(session)
            usage_repository = UsageSampleRepository(session)
            reporting_repository = ReportingRepository(session)

            demo_workspace = await workspace_repository.create(name="Demo Workspace")
            analytics_workspace = await workspace_repository.create(
                name="Analytics Sandbox"
            )
            await usage_repository.create(
                _usage_sample(
                    workspace_id=demo_workspace.id,
                    provider="sample-cloud",
                    region="sample-region-1",
                    measured_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                    energy_kwh=Decimal("0.500000"),
                    estimated_grams_co2e=Decimal("200.0000"),
                )
            )
            await usage_repository.create(
                _usage_sample(
                    workspace_id=demo_workspace.id,
                    provider="sample-cloud",
                    region="sample-region-2",
                    measured_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
                    energy_kwh=Decimal("0.250000"),
                    estimated_grams_co2e=Decimal("100.0000"),
                )
            )
            await usage_repository.create(
                _usage_sample(
                    workspace_id=analytics_workspace.id,
                    provider="demo-provider",
                    region="sample-region-1",
                    measured_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
                    energy_kwh=Decimal("1.000000"),
                    estimated_grams_co2e=Decimal("500.0000"),
                )
            )
            await session.commit()

            global_summary = await reporting_repository.summarize(
                ReportQuery(workspace_id=None, start_time=None, end_time=None)
            )
            filtered_summary = await reporting_repository.summarize(
                ReportQuery(
                    workspace_id=demo_workspace.id,
                    start_time=datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
                    end_time=datetime(2026, 2, 1, 0, 0, tzinfo=UTC),
                )
            )

        assert global_summary.total.usage_sample_count == 3
        assert global_summary.total.energy_kwh == Decimal("1.750000")
        assert global_summary.total.estimated_grams_co2e == Decimal("800.0000")
        assert [group.workspace_name for group in global_summary.by_workspace] == [
            "Analytics Sandbox",
            "Demo Workspace",
        ]
        assert [
            (group.provider, group.usage_sample_count, group.energy_kwh)
            for group in global_summary.by_provider
        ] == [
            ("demo-provider", 1, Decimal("1.000000")),
            ("sample-cloud", 2, Decimal("0.750000")),
        ]
        assert [
            (group.region, group.usage_sample_count, group.estimated_grams_co2e)
            for group in global_summary.by_region
        ] == [
            ("sample-region-1", 2, Decimal("700.0000")),
            ("sample-region-2", 1, Decimal("100.0000")),
        ]

        assert filtered_summary.time_range.start_time == datetime(
            2026,
            1,
            2,
            0,
            0,
            tzinfo=UTC,
        )
        assert filtered_summary.total.usage_sample_count == 1
        assert filtered_summary.total.energy_kwh == Decimal("0.250000")
        assert filtered_summary.by_workspace[0].workspace_id == demo_workspace.id
        assert filtered_summary.by_workspace[0].workspace_name == "Demo Workspace"
        assert filtered_summary.by_provider[0].provider == "sample-cloud"
        assert filtered_summary.by_region[0].region == "sample-region-2"
    finally:
        await engine.dispose()


def _usage_sample(
    *,
    workspace_id: UUID,
    provider: str,
    region: str,
    measured_at: datetime,
    energy_kwh: Decimal,
    estimated_grams_co2e: Decimal,
) -> UsageSampleCreate:
    return UsageSampleCreate(
        workspace_id=workspace_id,
        provider=provider,
        region=region,
        resource_type="vcpu",
        usage_amount=Decimal("10"),
        usage_unit="vcpu_hour",
        measured_at=measured_at,
        normalized_usage_amount=Decimal("10.000000"),
        normalized_usage_unit="vcpu_hour",
        energy_kwh=energy_kwh,
        carbon_intensity_grams_co2e_per_kwh=Decimal("400.0000"),
        estimated_grams_co2e=estimated_grams_co2e,
        factor_source="demo-static-v1",
    )


async def _create_database(admin_url: URL, database_name: str) -> None:
    await _run_admin_statements(
        admin_url,
        [f"CREATE DATABASE {_quote_identifier(database_name)}"],
    )


async def _drop_database(admin_url: URL, database_name: str) -> None:
    await _run_admin_statements(
        admin_url,
        [
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            "WHERE datname = :database_name AND pid <> pg_backend_pid()",
            f"DROP DATABASE IF EXISTS {_quote_identifier(database_name)}",
        ],
        parameters={"database_name": database_name},
    )


async def _run_admin_statements(
    admin_url: URL,
    statements: list[str],
    parameters: dict[str, str] | None = None,
) -> None:
    admin_database_url = admin_url.render_as_string(hide_password=False)
    engine = create_async_engine(
        admin_database_url,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    try:
        async with engine.connect() as connection:
            for statement in statements:
                await connection.execute(text(statement), parameters or {})
    finally:
        await engine.dispose()


def _quote_identifier(identifier: str) -> str:
    if not _DATABASE_IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"Unsafe database identifier: {identifier}")
    return f'"{identifier}"'
