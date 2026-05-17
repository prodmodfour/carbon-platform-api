"""FastAPI dependency wiring."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from carbon_platform_api.repositories.reports import ReportingRepository
from carbon_platform_api.repositories.usage_samples import UsageSampleRepository
from carbon_platform_api.repositories.workspaces import WorkspaceRepository
from carbon_platform_api.services.reporting import ReportingService
from carbon_platform_api.services.usage_ingestion import UsageIngestionService
from carbon_platform_api.services.workspaces import WorkspaceService


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an async database session with request-scoped transaction handling."""
    session_factory = cast(
        async_sessionmaker[AsyncSession],
        request.app.state.session_factory,
    )

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_workspace_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> WorkspaceService:
    """Build the workspace service for a request."""
    return WorkspaceService(WorkspaceRepository(session))


async def get_usage_ingestion_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UsageIngestionService:
    """Build the usage ingestion service for a request."""
    return UsageIngestionService(
        workspace_repository=WorkspaceRepository(session),
        usage_sample_repository=UsageSampleRepository(session),
    )


async def get_reporting_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ReportingService:
    """Build the reporting service for a request."""
    return ReportingService(
        report_repository=ReportingRepository(session),
        workspace_repository=WorkspaceRepository(session),
    )
