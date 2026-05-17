"""Tests for readiness service behaviour."""

from __future__ import annotations

import asyncio
import logging

import pytest

from carbon_platform_api.cache.health import RedisReadinessCheck, RedisReadinessError
from carbon_platform_api.services.readiness import ReadinessService


class FakeRedisHealthClient:
    """Fake Redis client for readiness check tests."""

    def __init__(self, ping_result: bool) -> None:
        self._ping_result = ping_result
        self.calls = 0

    async def ping(self) -> bool:
        """Return a configured ping result."""
        self.calls += 1
        return self._ping_result


class FakeReadinessCheck:
    """Fake dependency check for readiness service tests."""

    def __init__(self, name: str, error: Exception | None = None) -> None:
        self.name = name
        self._error = error
        self.calls = 0

    async def check(self) -> None:
        """Record the check and optionally raise a configured failure."""
        self.calls += 1
        if self._error is not None:
            raise self._error


def test_redis_readiness_check_passes_when_ping_succeeds() -> None:
    """A true Redis ping response should pass readiness."""
    redis_client = FakeRedisHealthClient(ping_result=True)

    asyncio.run(RedisReadinessCheck(redis_client).check())

    assert redis_client.calls == 1


def test_redis_readiness_check_fails_when_ping_is_false() -> None:
    """A false Redis ping response should fail readiness."""
    redis_client = FakeRedisHealthClient(ping_result=False)

    with pytest.raises(RedisReadinessError):
        asyncio.run(RedisReadinessCheck(redis_client).check())

    assert redis_client.calls == 1


def test_readiness_service_reports_ready_when_all_dependencies_pass() -> None:
    """All passing checks should produce a ready result."""
    database_check = FakeReadinessCheck("database")
    redis_check = FakeReadinessCheck("redis")
    service = ReadinessService(checks=(database_check, redis_check))

    result = asyncio.run(service.check_readiness())

    assert result.status == "ready"
    assert [(item.name, item.status) for item in result.dependencies] == [
        ("database", "ok"),
        ("redis", "ok"),
    ]
    assert database_check.calls == 1
    assert redis_check.calls == 1


def test_readiness_service_reports_failures_without_leaking_error_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failing checks should be logged with safe structured fields only."""
    database_check = FakeReadinessCheck("database")
    redis_check = FakeReadinessCheck("redis", RuntimeError("sample connection detail"))
    service = ReadinessService(checks=(database_check, redis_check))

    caplog.set_level(logging.WARNING, logger="carbon_platform_api.readiness")
    result = asyncio.run(service.check_readiness())

    assert result.status == "not_ready"
    assert [(item.name, item.status) for item in result.dependencies] == [
        ("database", "ok"),
        ("redis", "error"),
    ]
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.getMessage() == "readiness_dependency_failed"
    assert record.__dict__["dependency"] == "redis"
    assert record.__dict__["error_type"] == "RuntimeError"
    assert "sample connection detail" not in caplog.text
