"""Workspace repository backed by SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from carbon_platform_api.models.workspace import Workspace


class WorkspaceRepository:
    """Persistence operations for workspaces only."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a repository using an externally managed session."""
        self._session = session

    async def create(self, *, name: str) -> Workspace:
        """Create a workspace and flush it to the current transaction."""
        workspace = Workspace(name=name)
        self._session.add(workspace)
        await self._session.flush()
        await self._session.refresh(workspace)
        return workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        """Fetch a workspace by primary key."""
        return await self._session.get(Workspace, workspace_id)

    async def list(self) -> list[Workspace]:
        """List workspaces in deterministic name order."""
        result = await self._session.scalars(
            select(Workspace).order_by(Workspace.name, Workspace.id)
        )
        return list(result)
