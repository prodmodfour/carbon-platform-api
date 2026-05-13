"""FastAPI application entrypoint."""

from fastapi import FastAPI

from carbon_platform_api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="carbon-platform-api",
        version="0.1.0",
        description=(
            "Public portfolio API skeleton for compute-related carbon usage tracking."
        ),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(health_router)
    return app


app = create_app()
