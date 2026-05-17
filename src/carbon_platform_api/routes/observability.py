"""Operational observability HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from carbon_platform_api.dependencies import get_metrics_service, get_readiness_service
from carbon_platform_api.schemas.observability import ReadinessResponse
from carbon_platform_api.services.metrics import (
    PROMETHEUS_TEXT_CONTENT_TYPE,
    MetricsService,
)
from carbon_platform_api.services.readiness import ReadinessService

router = APIRouter(tags=["observability"])


@router.get(
    "/readyz",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def read_readyz(
    response: Response,
    readiness_service: Annotated[ReadinessService, Depends(get_readiness_service)],
) -> ReadinessResponse:
    """Return dependency readiness for the API."""
    readiness = await readiness_service.check_readiness()
    if readiness.status == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse.model_validate(readiness)


@router.get("/metrics", include_in_schema=False)
def read_metrics(
    metrics_service: Annotated[MetricsService, Depends(get_metrics_service)],
) -> Response:
    """Return Prometheus-compatible metrics text."""
    return Response(
        content=metrics_service.render_prometheus_text(),
        media_type=PROMETHEUS_TEXT_CONTENT_TYPE,
    )
