"""Health check routes."""

from fastapi import APIRouter

from carbon_platform_api.schemas.health import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthCheckResponse)
def read_healthz() -> HealthCheckResponse:
    """Return a minimal liveness response."""
    return HealthCheckResponse(status="ok")
