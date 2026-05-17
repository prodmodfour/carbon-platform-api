"""Tests for workspace API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from carbon_platform_api.config import Settings
from carbon_platform_api.dependencies import get_workspace_service
from carbon_platform_api.main import create_app
from carbon_platform_api.repositories.workspaces import WorkspaceRecord
from carbon_platform_api.services.workspaces import WorkspaceService


def default_settings() -> Settings:
    """Return deterministic settings for endpoint tests."""
    return Settings(
        app_name="carbon-platform-api",
        app_version="0.1.0",
        environment="local",
        log_level="INFO",
        docs_enabled=False,
    )


class FakeWorkspaceRepository:
    """In-memory workspace repository for endpoint tests."""

    def __init__(self) -> None:
        self._workspaces: dict[UUID, WorkspaceRecord] = {}
        self._current_time = datetime(2026, 1, 1, tzinfo=UTC)

    async def create(self, *, name: str) -> WorkspaceRecord:
        """Create a workspace record in memory."""
        created_at = self._next_timestamp()
        workspace = WorkspaceRecord(
            id=uuid4(),
            name=name,
            created_at=created_at,
            updated_at=created_at,
        )
        self._workspaces[workspace.id] = workspace
        return workspace

    async def get(self, workspace_id: UUID) -> WorkspaceRecord | None:
        """Fetch a workspace by ID from memory."""
        return self._workspaces.get(workspace_id)

    async def get_by_name(self, name: str) -> WorkspaceRecord | None:
        """Fetch a workspace by unique name from memory."""
        for workspace in self._workspaces.values():
            if workspace.name == name:
                return workspace
        return None

    async def list(self) -> list[WorkspaceRecord]:
        """List workspace records in deterministic order."""
        return sorted(
            self._workspaces.values(),
            key=lambda workspace: (workspace.name, str(workspace.id)),
        )

    def _next_timestamp(self) -> datetime:
        timestamp = self._current_time
        self._current_time += timedelta(seconds=1)
        return timestamp


def create_workspace_client(repository: FakeWorkspaceRepository) -> TestClient:
    """Create a test client with the workspace service dependency overridden."""
    app = create_app(settings=default_settings())

    def override_get_workspace_service() -> WorkspaceService:
        return WorkspaceService(repository)

    app.dependency_overrides[get_workspace_service] = override_get_workspace_service
    return TestClient(app)


def test_workspace_endpoints_create_list_and_fetch_workspaces() -> None:
    """Workspace endpoints should create, list, and fetch records through services."""
    client = create_workspace_client(FakeWorkspaceRepository())

    create_response = client.post("/workspaces", json={"name": " Demo Workspace "})

    assert create_response.status_code == 201
    created_workspace = create_response.json()
    assert UUID(created_workspace["id"])
    assert created_workspace["name"] == "Demo Workspace"
    assert "created_at" in created_workspace
    assert "updated_at" in created_workspace

    list_response = client.get("/workspaces")
    fetch_response = client.get(f"/workspaces/{created_workspace['id']}")

    assert list_response.status_code == 200
    assert list_response.json() == [created_workspace]
    assert fetch_response.status_code == 200
    assert fetch_response.json() == created_workspace


def test_create_workspace_returns_clear_duplicate_name_error() -> None:
    """Duplicate workspace names should return a clear client error."""
    client = create_workspace_client(FakeWorkspaceRepository())

    first_response = client.post("/workspaces", json={"name": "Demo Workspace"})
    duplicate_response = client.post("/workspaces", json={"name": "Demo Workspace"})

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {"detail": "Workspace name already exists."}


def test_get_workspace_returns_clear_missing_workspace_error() -> None:
    """Missing workspace IDs should return a clear 404 response."""
    client = create_workspace_client(FakeWorkspaceRepository())

    response = client.get(f"/workspaces/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found."}
