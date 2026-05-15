# Architecture

## Current scope

T003 provides the FastAPI skeleton, a liveness endpoint, environment-backed configuration, structured JSON request logging, request ID middleware, and Docker support for local development. Docker Compose starts three services: the API, PostgreSQL, and Redis.

PostgreSQL and Redis are infrastructure only in this ticket. The application intentionally does not include database models, migrations, Redis application code, carbon calculations, authentication, metrics, or external API clients yet.

## Package layout

```text
src/carbon_platform_api/
  config.py                   Pydantic settings loaded from CARBON_API_* variables
  logging.py                  Standard-library JSON logging formatter/configuration
  main.py                     FastAPI app factory and ASGI app
  middleware/request_id.py    Request ID response header and completion logging
  routes/health.py            HTTP route for GET /healthz
  schemas/health.py           Response schema for the health endpoint
```

## Configuration

Application configuration is centralized in `carbon_platform_api.config.Settings` and loaded from environment variables with the `CARBON_API_` prefix.

Current settings:

- `app_name`
- `app_version`
- `environment`
- `log_level`
- `docs_enabled`

FastAPI documentation and OpenAPI routes remain disabled by default. They are only exposed when `CARBON_API_DOCS_ENABLED=true`.

## Logging and request correlation

`carbon_platform_api.logging` configures a standard-library JSON log formatter. Request completion logs are emitted by `RequestIdMiddleware` and include:

- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

The middleware propagates an inbound `X-Request-ID` header when supplied. If no request ID is supplied, it generates one and adds it to the response. The same request ID is included in the completion log.

## Local infrastructure

```text
docker-compose.yml
  api                  FastAPI/Uvicorn container exposed on host port 8000
  postgres             PostgreSQL container exposed on host port 5432
  redis                Redis container exposed on host port 6379
```

The API container runs as a non-root user and has a container health check that calls `GET /healthz`. PostgreSQL and Redis have image-native health checks.

## Dependency direction

The project follows this dependency direction as features are added:

```text
routes -> schemas -> services -> repositories/clients -> database/cache/external APIs
```

Only HTTP routes, schemas, configuration, logging, and middleware exist in the application code because there is no business logic, persistence, cache, or external integration yet. Route handlers are limited to HTTP concerns and typed response construction.

## API surface

- `GET /healthz` returns a JSON liveness payload and an `X-Request-ID` response header.

FastAPI documentation and OpenAPI routes are disabled by default so the only default exposed endpoint is `/healthz`.
