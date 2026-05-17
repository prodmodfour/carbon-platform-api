"""Workspace repository backed by SQLAlchemy."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from carbon_platform_api.models.workspace import Workspace


@dataclass(frozen=True, slots=True)
class WorkspaceRecord:
    """Repository-level workspace data returned to services."""

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class WorkspaceRepository:
    """Persistence operations for workspaces only."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a repository using an externally managed session."""
        self._session = session

    async def create(self, *, name: str) -> WorkspaceRecord:
        """Create a workspace and flush it to the current transaction."""
        workspace = Workspace(name=name)
        self._session.add(workspace)
        await self._session.flush()
        await self._session.refresh(workspace)
        return _to_record(workspace)

    async def get(self, workspace_id: UUID) -> WorkspaceRecord | None:
        """Fetch a workspace by primary key."""
        workspace = await self._session.get(Workspace, workspace_id)
        if workspace is None:
            return None
        return _to_record(workspace)

    async def get_by_name(self, name: str) -> WorkspaceRecord | None:
        """Fetch a workspace by its unique name."""
        workspace = await self._session.scalar(
            select(Workspace).where(Workspace.name == name)
        )
        if workspace is None:
            return None
        return _to_record(workspace)

    async def list(self) -> list[WorkspaceRecord]:
        """List workspaces in deterministic name order."""
        result = await self._session.scalars(
            select(Workspace).order_by(Workspace.name, Workspace.id)
        )
        return [_to_record(workspace) for workspace in result]


def _to_record(workspace: Workspace) -> WorkspaceRecord:
    return WorkspaceRecord(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )
