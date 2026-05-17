"""Workspace HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from carbon_platform_api.dependencies import (
    get_usage_ingestion_service,
    get_workspace_service,
    require_api_key,
)
from carbon_platform_api.schemas.usage_samples import (
    UsageSampleIngestionRequest,
    UsageSampleResponse,
)
from carbon_platform_api.schemas.workspaces import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
)
from carbon_platform_api.services.usage_ingestion import (
    InvalidUsageSampleError,
    UsageIngestionService,
    UsageSampleWorkspaceNotFoundError,
)
from carbon_platform_api.services.workspaces import (
    DuplicateWorkspaceNameError,
    WorkspaceNotFoundError,
    WorkspaceService,
)

router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(require_api_key)],
)


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


@router.post(
    "/{workspace_id}/usage-samples",
    response_model=UsageSampleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_usage_sample(
    workspace_id: UUID,
    request: UsageSampleIngestionRequest,
    usage_ingestion_service: Annotated[
        UsageIngestionService,
        Depends(get_usage_ingestion_service),
    ],
) -> UsageSampleResponse:
    """Ingest one compute usage sample for a workspace."""
    try:
        usage_sample = await usage_ingestion_service.ingest_usage_sample(
            workspace_id=workspace_id,
            request=request,
        )
    except UsageSampleWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        ) from exc
    except InvalidUsageSampleError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return UsageSampleResponse.model_validate(usage_sample)
