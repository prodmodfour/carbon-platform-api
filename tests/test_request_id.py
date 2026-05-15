"""Tests for request ID middleware and structured request logging."""

import io
import json
import logging
from uuid import UUID

from fastapi.testclient import TestClient

from carbon_platform_api.config import Settings
from carbon_platform_api.logging import JsonFormatter
from carbon_platform_api.main import create_app
from carbon_platform_api.middleware.request_id import REQUEST_LOGGER_NAME


def default_settings() -> Settings:
    """Return deterministic settings for app factory tests."""
    return Settings(
        app_name="carbon-platform-api",
        app_version="0.1.0",
        environment="local",
        log_level="INFO",
        docs_enabled=False,
    )


def test_healthz_response_includes_generated_request_id() -> None:
    """Responses should include a generated request ID when no ID is supplied."""
    client = TestClient(create_app(settings=default_settings()))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id)


def test_healthz_response_propagates_supplied_request_id() -> None:
    """Responses should propagate an inbound X-Request-ID header."""
    client = TestClient(create_app(settings=default_settings()))

    response = client.get("/healthz", headers={"X-Request-ID": "test-request-id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-id"


def test_docs_and_openapi_are_disabled_by_default() -> None:
    """FastAPI docs and OpenAPI routes should stay disabled unless configured."""
    client = TestClient(create_app(settings=default_settings()))

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_request_completion_log_is_structured_json() -> None:
    """Completed requests should emit structured JSON logs with request metadata."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    request_logger = logging.getLogger(REQUEST_LOGGER_NAME)
    request_logger.addHandler(handler)

    try:
        client = TestClient(create_app(settings=default_settings()))
        response = client.get("/healthz", headers={"X-Request-ID": "log-test-id"})
    finally:
        request_logger.removeHandler(handler)

    log_lines = [line for line in stream.getvalue().splitlines() if line]
    assert log_lines

    log_event = json.loads(log_lines[-1])
    assert log_event["message"] == "request_completed"
    assert log_event["request_id"] == "log-test-id"
    assert log_event["method"] == "GET"
    assert log_event["path"] == "/healthz"
    assert log_event["status_code"] == 200
    assert isinstance(log_event["duration_ms"], int | float)
    assert response.headers["X-Request-ID"] == "log-test-id"
