"""Workspace business service."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from carbon_platform_api.repositories.workspaces import WorkspaceRecord


class WorkspaceRepositoryProtocol(Protocol):
    """Persistence operations required by the workspace service."""

    async def create(self, *, name: str) -> WorkspaceRecord:
        """Persist a new workspace."""
        ...

    async def get(self, workspace_id: UUID) -> WorkspaceRecord | None:
        """Fetch a workspace by primary key."""
        ...

    async def get_by_name(self, name: str) -> WorkspaceRecord | None:
        """Fetch a workspace by its unique name."""
        ...

    async def list(self) -> list[WorkspaceRecord]:
        """List workspaces."""
        ...


class DuplicateWorkspaceNameError(ValueError):
    """Raised when a workspace name is already in use."""


class WorkspaceNotFoundError(LookupError):
    """Raised when a workspace does not exist."""


class WorkspaceService:
    """Business operations for workspaces."""

    def __init__(self, repository: WorkspaceRepositoryProtocol) -> None:
        """Create a service using a small repository abstraction."""
        self._repository = repository

    async def create_workspace(self, *, name: str) -> WorkspaceRecord:
        """Create a workspace after enforcing name uniqueness."""
        normalized_name = name.strip()
        existing_workspace = await self._repository.get_by_name(normalized_name)
        if existing_workspace is not None:
            raise DuplicateWorkspaceNameError(normalized_name)
        return await self._repository.create(name=normalized_name)

    async def list_workspaces(self) -> list[WorkspaceRecord]:
        """List all workspaces in repository-defined deterministic order."""
        return await self._repository.list()

    async def get_workspace(self, workspace_id: UUID) -> WorkspaceRecord:
        """Fetch a workspace or raise a service-level missing-resource error."""
        workspace = await self._repository.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(str(workspace_id))
        return workspace
