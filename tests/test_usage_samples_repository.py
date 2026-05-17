"""Integration tests for usage sample persistence using PostgreSQL."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from carbon_platform_api.db.base import Base
from carbon_platform_api.db.session import (
    create_database_engine,
    create_session_factory,
)
from carbon_platform_api.models.usage_sample import UsageSample
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


def test_usage_sample_repository_persists_calculated_estimates(
    postgres_database_url: str,
) -> None:
    """Usage sample repository should store raw usage and calculated estimates."""
    asyncio.run(_exercise_usage_sample_repository(postgres_database_url))


async def _exercise_usage_sample_repository(database_url: str) -> None:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            workspace_repository = WorkspaceRepository(session)
            usage_repository = UsageSampleRepository(session)
            workspace = await workspace_repository.create(name="Demo Workspace")
            created_sample = await usage_repository.create(
                UsageSampleCreate(
                    workspace_id=workspace.id,
                    provider="sample-cloud",
                    region="sample-region-1",
                    resource_type="vcpu",
                    usage_amount=Decimal("10"),
                    usage_unit="vcpu_hour",
                    measured_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                    normalized_usage_amount=Decimal("10.000000"),
                    normalized_usage_unit="vcpu_hour",
                    energy_kwh=Decimal("0.500000"),
                    carbon_intensity_grams_co2e_per_kwh=Decimal("400.0000"),
                    estimated_grams_co2e=Decimal("200.0000"),
                    factor_source="demo-static-v1",
                )
            )
            await session.commit()

        async with session_factory() as session:
            persisted_sample = await session.get(UsageSample, created_sample.id)

        assert persisted_sample is not None
        assert persisted_sample.workspace_id == workspace.id
        assert persisted_sample.provider == "sample-cloud"
        assert persisted_sample.region == "sample-region-1"
        assert persisted_sample.resource_type == "vcpu"
        assert persisted_sample.usage_amount == Decimal("10.000000")
        assert persisted_sample.usage_unit == "vcpu_hour"
        assert persisted_sample.normalized_usage_amount == Decimal("10.000000")
        assert persisted_sample.normalized_usage_unit == "vcpu_hour"
        assert persisted_sample.energy_kwh == Decimal("0.500000")
        assert persisted_sample.carbon_intensity_grams_co2e_per_kwh == Decimal(
            "400.0000"
        )
        assert persisted_sample.estimated_grams_co2e == Decimal("200.0000")
        assert persisted_sample.factor_source == "demo-static-v1"
    finally:
        await engine.dispose()


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
