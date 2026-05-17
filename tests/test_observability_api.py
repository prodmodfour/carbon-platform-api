"""Tests for readiness and metrics endpoints."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from carbon_platform_api.config import Settings
from carbon_platform_api.dependencies import get_readiness_service
from carbon_platform_api.main import create_app
from carbon_platform_api.services.readiness import (
    DependencyReadiness,
    ReadinessResult,
)


def default_settings() -> Settings:
    """Return deterministic settings for observability endpoint tests."""
    return Settings(
        app_name="carbon-platform-api",
        app_version="0.1.0",
        environment="local",
        log_level="INFO",
        docs_enabled=False,
    )


class FakeReadinessService:
    """Fake readiness service for endpoint tests."""

    def __init__(self, result: ReadinessResult) -> None:
        self._result = result

    async def check_readiness(self) -> ReadinessResult:
        """Return a configured readiness result."""
        return self._result


def create_observability_client(readiness_result: ReadinessResult) -> TestClient:
    """Create a test client with readiness dependency overridden."""
    app = create_app(settings=default_settings())

    def override_get_readiness_service() -> FakeReadinessService:
        return FakeReadinessService(readiness_result)

    app.dependency_overrides[get_readiness_service] = override_get_readiness_service
    return TestClient(app)


def test_readyz_returns_dependency_status_when_healthy() -> None:
    """GET /readyz should return dependency status for a ready API."""
    readiness = ReadinessResult(
        status="ready",
        dependencies=(
            DependencyReadiness(name="database", status="ok"),
            DependencyReadiness(name="redis", status="ok"),
        ),
    )

    with create_observability_client(readiness) as client:
        response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": [
            {"name": "database", "status": "ok"},
            {"name": "redis", "status": "ok"},
        ],
    }


def test_readyz_returns_503_when_a_dependency_is_unhealthy() -> None:
    """GET /readyz should return a clear unhealthy status."""
    readiness = ReadinessResult(
        status="not_ready",
        dependencies=(
            DependencyReadiness(name="database", status="ok"),
            DependencyReadiness(name="redis", status="error"),
        ),
    )

    with create_observability_client(readiness) as client:
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": [
            {"name": "database", "status": "ok"},
            {"name": "redis", "status": "error"},
        ],
    }


def test_metrics_returns_prometheus_text_with_process_and_http_metrics() -> None:
    """GET /metrics should expose Prometheus process and HTTP request metrics."""
    app = create_app(settings=default_settings())

    with TestClient(app) as client:
        health_response = client.get("/healthz")
        metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")

    body = metrics_response.text
    assert "# HELP process_cpu_seconds_total" in body
    assert "# HELP carbon_api_http_requests_total" in body
    assert "# TYPE carbon_api_http_requests_total counter" in body
    assert "# HELP carbon_api_http_request_duration_seconds" in body
    assert "# TYPE carbon_api_http_request_duration_seconds histogram" in body
    assert re.search(
        r'carbon_api_http_requests_total\{method="GET",path="/healthz",'
        r'status_code="200"\} 1\.0',
        body,
    )
