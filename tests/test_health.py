"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from carbon_platform_api.main import create_app


def test_healthz_returns_ok() -> None:
    """GET /healthz returns the expected liveness payload."""
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
