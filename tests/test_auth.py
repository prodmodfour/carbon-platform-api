"""Tests for API key authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from carbon_platform_api.config import Settings
from carbon_platform_api.dependencies import (
    get_readiness_service,
    get_workspace_service,
)
from carbon_platform_api.main import create_app
from carbon_platform_api.repositories.workspaces import WorkspaceRecord
from carbon_platform_api.services.auth import (
    ApiKeyAuthenticationError,
    ApiKeyAuthService,
)
from carbon_platform_api.services.readiness import (
    DependencyReadiness,
    ReadinessResult,
)

_AUTH_KEY = "local-test-key"
_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


def auth_settings(*, auth_enabled: bool = True) -> Settings:
    """Return deterministic settings for auth endpoint tests."""
    return Settings(
        app_name="carbon-platform-api",
        app_version="0.1.0",
        environment="local",
        log_level="INFO",
        docs_enabled=False,
        auth_enabled=auth_enabled,
        auth_api_keys=SecretStr(f"{_AUTH_KEY},secondary-local-test-key"),
    )


class FakeWorkspaceService:
    """Fake workspace service for authentication endpoint tests."""

    def __init__(self) -> None:
        self.calls = 0

    async def list_workspaces(self) -> list[WorkspaceRecord]:
        """Return one deterministic workspace."""
        self.calls += 1
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        return [
            WorkspaceRecord(
                id=_WORKSPACE_ID,
                name="Demo Workspace",
                created_at=timestamp,
                updated_at=timestamp,
            )
        ]


class FakeReadinessService:
    """Fake readiness service for unprotected operational endpoint tests."""

    async def check_readiness(self) -> ReadinessResult:
        """Return healthy dependency status."""
        return ReadinessResult(
            status="ready",
            dependencies=(
                DependencyReadiness(name="database", status="ok"),
                DependencyReadiness(name="redis", status="ok"),
            ),
        )


def create_auth_client(
    *,
    auth_enabled: bool = True,
    workspace_service: FakeWorkspaceService | None = None,
) -> TestClient:
    """Create a test client with service dependencies overridden."""
    app = create_app(settings=auth_settings(auth_enabled=auth_enabled))
    fake_workspace_service = workspace_service or FakeWorkspaceService()

    def override_get_workspace_service() -> FakeWorkspaceService:
        return fake_workspace_service

    def override_get_readiness_service() -> FakeReadinessService:
        return FakeReadinessService()

    app.dependency_overrides[get_workspace_service] = override_get_workspace_service
    app.dependency_overrides[get_readiness_service] = override_get_readiness_service
    return TestClient(app)


def test_auth_service_noops_when_authentication_is_disabled() -> None:
    """Disabled auth should not require callers to provide API keys."""
    service = ApiKeyAuthService(auth_enabled=False, api_keys=())

    service.validate_api_key(None)


def test_auth_service_rejects_missing_and_invalid_keys_when_enabled() -> None:
    """Enabled auth should reject missing or unrecognized keys."""
    service = ApiKeyAuthService(auth_enabled=True, api_keys=(_AUTH_KEY,))

    with pytest.raises(ApiKeyAuthenticationError):
        service.validate_api_key(None)
    with pytest.raises(ApiKeyAuthenticationError):
        service.validate_api_key("wrong-local-key")


def test_business_endpoint_rejects_missing_api_key_when_auth_enabled() -> None:
    """Protected business endpoints should reject requests without API keys."""
    workspace_service = FakeWorkspaceService()
    client = create_auth_client(workspace_service=workspace_service)

    response = client.get("/workspaces")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key."}
    assert workspace_service.calls == 0


def test_business_endpoint_rejects_invalid_api_key_when_auth_enabled() -> None:
    """Protected business endpoints should reject invalid API keys."""
    workspace_service = FakeWorkspaceService()
    client = create_auth_client(workspace_service=workspace_service)

    response = client.get("/workspaces", headers={"X-API-Key": "wrong-local-key"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key."}
    assert workspace_service.calls == 0


def test_business_endpoint_accepts_valid_api_key_when_auth_enabled() -> None:
    """Protected business endpoints should accept configured API keys."""
    workspace_service = FakeWorkspaceService()
    client = create_auth_client(workspace_service=workspace_service)

    response = client.get("/workspaces", headers={"X-API-Key": _AUTH_KEY})

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(_WORKSPACE_ID)
    assert response.json()[0]["name"] == "Demo Workspace"
    assert workspace_service.calls == 1


def test_report_endpoint_requires_api_key_when_auth_enabled() -> None:
    """Reporting endpoints are business endpoints and should be protected."""
    client = create_auth_client()

    response = client.get("/reports/summary")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key."}


def test_business_endpoint_allows_requests_when_auth_disabled() -> None:
    """Business endpoints should remain usable without keys when auth is disabled."""
    client = create_auth_client(auth_enabled=False)

    response = client.get("/workspaces")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Demo Workspace"


def test_operational_endpoints_remain_unprotected_when_auth_enabled() -> None:
    """Health, readiness, and metrics should not require API keys."""
    client = create_auth_client()

    health_response = client.get("/healthz")
    readiness_response = client.get("/readyz")
    metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert readiness_response.status_code == 200
    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")
