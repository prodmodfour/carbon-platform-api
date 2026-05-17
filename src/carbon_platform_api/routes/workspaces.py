"""Workspace HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from carbon_platform_api.dependencies import get_workspace_service
from carbon_platform_api.schemas.workspaces import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
)
from carbon_platform_api.services.workspaces import (
    DuplicateWorkspaceNameError,
    WorkspaceNotFoundError,
    WorkspaceService,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    request: WorkspaceCreateRequest,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    """Create a workspace."""
    try:
        workspace = await workspace_service.create_workspace(name=request.name)
    except DuplicateWorkspaceNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workspace name already exists.",
        ) from exc

    return WorkspaceResponse.model_validate(workspace)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> list[WorkspaceResponse]:
    """List workspaces."""
    workspaces = await workspace_service.list_workspaces()
    return [WorkspaceResponse.model_validate(workspace) for workspace in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    """Fetch one workspace by ID."""
    try:
        workspace = await workspace_service.get_workspace(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        ) from exc

    return WorkspaceResponse.model_validate(workspace)
