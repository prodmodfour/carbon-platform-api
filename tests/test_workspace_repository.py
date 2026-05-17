"""Integration tests for the workspace repository using PostgreSQL."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Iterator
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


def test_workspace_repository_creates_lists_and_fetches_workspaces(
    postgres_database_url: str,
) -> None:
    """Workspace repository should persist and read workspaces through PostgreSQL."""
    asyncio.run(_exercise_workspace_repository(postgres_database_url))


async def _exercise_workspace_repository(database_url: str) -> None:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            repository = WorkspaceRepository(session)

            first_workspace = await repository.create(name="Demo Workspace")
            second_workspace = await repository.create(name="Analytics Sandbox")
            await session.commit()

            fetched_workspace = await repository.get(first_workspace.id)
            missing_workspace = await repository.get(uuid4())
            workspaces = await repository.list()

        assert fetched_workspace is not None
        assert fetched_workspace.id == first_workspace.id
        assert fetched_workspace.name == "Demo Workspace"
        assert missing_workspace is None
        assert [workspace.id for workspace in workspaces] == [
            second_workspace.id,
            first_workspace.id,
        ]
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
