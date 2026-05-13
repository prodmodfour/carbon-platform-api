# Architecture

## Current scope

T002 provides the initial FastAPI skeleton, a liveness endpoint, and Docker support for local development. Docker Compose starts three services: the API, PostgreSQL, and Redis.

PostgreSQL and Redis are infrastructure only in this ticket. The application intentionally does not include database models, migrations, Redis application code, carbon calculations, authentication, metrics, or external API clients yet.

## Package layout

```text
src/carbon_platform_api/
  main.py              FastAPI app factory and ASGI app
  routes/health.py     HTTP route for GET /healthz
  schemas/health.py    Response schema for the health endpoint
```

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

Only `routes` and `schemas` exist in the application code because there is no business logic, persistence, cache, or external integration yet. Route handlers are limited to HTTP concerns and typed response construction.

## API surface

- `GET /healthz` returns a JSON liveness payload.

FastAPI documentation and OpenAPI routes are disabled for the skeleton so the only exposed endpoint is `/healthz`. API documentation endpoints can be introduced deliberately in a future ticket.
