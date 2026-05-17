"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from carbon_platform_api.cache.carbon_intensity import create_redis_client
from carbon_platform_api.config import Settings, get_settings
from carbon_platform_api.db.session import (
    create_database_engine,
    create_session_factory,
)
from carbon_platform_api.logging import configure_logging
from carbon_platform_api.metrics import create_prometheus_metrics
from carbon_platform_api.middleware.metrics import RequestMetricsMiddleware
from carbon_platform_api.middleware.request_id import RequestIdMiddleware
from carbon_platform_api.routes.health import router as health_router
from carbon_platform_api.routes.observability import router as observability_router
from carbon_platform_api.routes.reports import router as reports_router
from carbon_platform_api.routes.workspaces import router as workspace_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved_settings = settings if settings is not None else get_settings()
    configure_logging(resolved_settings.log_level)

    docs_url = "/docs" if resolved_settings.docs_enabled else None
    redoc_url = "/redoc" if resolved_settings.docs_enabled else None
    openapi_url = "/openapi.json" if resolved_settings.docs_enabled else None

    database_engine = create_database_engine(resolved_settings.database_url)
    session_factory = create_session_factory(database_engine)
    redis_client = create_redis_client(resolved_settings.redis_url)
    metrics = create_prometheus_metrics()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            try:
                await redis_client.aclose()
            finally:
                await database_engine.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=("Public portfolio API for compute-related carbon usage tracking."),
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database_engine = database_engine
    app.state.session_factory = session_factory
    app.state.redis_client = redis_client
    app.state.metrics_registry = metrics.registry
    app.add_middleware(RequestMetricsMiddleware, recorder=metrics.http_recorder)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router)
    app.include_router(observability_router)
    app.include_router(workspace_router)
    app.include_router(reports_router)
    return app


app = create_app()
