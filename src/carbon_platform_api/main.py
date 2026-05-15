"""FastAPI application entrypoint."""

from fastapi import FastAPI

from carbon_platform_api.config import Settings, get_settings
from carbon_platform_api.logging import configure_logging
from carbon_platform_api.middleware.request_id import RequestIdMiddleware
from carbon_platform_api.routes.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved_settings = settings if settings is not None else get_settings()
    configure_logging(resolved_settings.log_level)

    docs_url = "/docs" if resolved_settings.docs_enabled else None
    redoc_url = "/redoc" if resolved_settings.docs_enabled else None
    openapi_url = "/openapi.json" if resolved_settings.docs_enabled else None

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "Public portfolio API skeleton for compute-related carbon usage tracking."
        ),
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router)
    return app


app = create_app()
