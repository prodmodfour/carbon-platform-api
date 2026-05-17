"""Readiness service for dependency health checks."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

READINESS_LOGGER_NAME = "carbon_platform_api.readiness"
DependencyStatus = Literal["ok", "error"]
ReadinessStatus = Literal["ready", "not_ready"]


class ReadinessCheckProtocol(Protocol):
    """Small interface implemented by dependency readiness checks."""

    name: str

    async def check(self) -> None:
        """Raise an exception when the dependency is not ready."""
        ...


@dataclass(frozen=True)
class DependencyReadiness:
    """Readiness result for one dependency."""

    name: str
    status: DependencyStatus


@dataclass(frozen=True)
class ReadinessResult:
    """Overall readiness result."""

    status: ReadinessStatus
    dependencies: tuple[DependencyReadiness, ...]


class ReadinessService:
    """Coordinate readiness checks without exposing dependency internals."""

    def __init__(
        self,
        checks: Sequence[ReadinessCheckProtocol],
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        """Create a readiness service for a sequence of dependency checks."""
        self._checks = tuple(checks)
        self._logger = logger or logging.getLogger(READINESS_LOGGER_NAME)

    async def check_readiness(self) -> ReadinessResult:
        """Run all dependency checks and return an aggregate readiness result."""
        dependency_results: list[DependencyReadiness] = []

        for check in self._checks:
            try:
                await check.check()
            except Exception as exc:  # noqa: BLE001 - readiness must report all failures.
                self._logger.warning(
                    "readiness_dependency_failed",
                    extra={
                        "dependency": check.name,
                        "error_type": type(exc).__name__,
                    },
                )
                dependency_results.append(
                    DependencyReadiness(name=check.name, status="error")
                )
            else:
                dependency_results.append(
                    DependencyReadiness(name=check.name, status="ok")
                )

        overall_status: ReadinessStatus = (
            "ready"
            if all(result.status == "ok" for result in dependency_results)
            else "not_ready"
        )
        return ReadinessResult(
            status=overall_status,
            dependencies=tuple(dependency_results),
        )
