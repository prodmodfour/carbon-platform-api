"""Schemas for health check responses."""

from typing import Literal

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Response body returned by the liveness endpoint."""

    status: Literal["ok"]
