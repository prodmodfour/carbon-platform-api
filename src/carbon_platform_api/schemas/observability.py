"""Schemas for operational observability endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DependencyReadinessResponse(BaseModel):
    """Readiness status for one runtime dependency."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    status: Literal["ok", "error"]


class ReadinessResponse(BaseModel):
    """Readiness endpoint response."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["ready", "not_ready"]
    dependencies: list[DependencyReadinessResponse]
