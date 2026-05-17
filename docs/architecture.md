# Architecture

## Current scope

T004 provides the FastAPI skeleton, a liveness endpoint, environment-backed configuration, structured JSON request logging, request ID middleware, Docker support for local development, and initial PostgreSQL persistence. Persistence currently includes SQLAlchemy models, Alembic migrations, async database/session helpers, and a workspace repository.

Redis is still infrastructure only. The application intentionally does not include workspace API endpoints, Redis application code, carbon calculations, authentication, metrics, or external API clients yet.

## Package layout

```text
src/carbon_platform_api/
  config.py                         Pydantic settings loaded from CARBON_API_* variables
  logging.py                        Standard-library JSON logging formatter/configuration
  main.py                           FastAPI app factory and ASGI app
  db/base.py                        SQLAlchemy declarative base and naming convention
  db/session.py                     Async SQLAlchemy engine/session factory helpers
  middleware/request_id.py          Request ID response header and completion logging
  models/                           SQLAlchemy persistence models
  repositories/workspaces.py        Workspace repository using an async SQLAlchemy session
  routes/health.py                  HTTP route for GET /healthz
  schemas/health.py                 Response schema for the health endpoint
alembic/
  env.py                            Async Alembic migration environment
  versions/                         Database schema migrations
```

## Configuration

Application configuration is centralized in `carbon_platform_api.config.Settings` and loaded from environment variables with the `CARBON_API_` prefix.

Current settings:

- `app_name`
- `app_version`
- `environment`
- `log_level`
- `docs_enabled`
- `database_url`

FastAPI documentation and OpenAPI routes remain disabled by default. They are only exposed when `CARBON_API_DOCS_ENABLED=true`.

## Logging and request correlation

`carbon_platform_api.logging` configures a standard-library JSON log formatter. Request completion logs are emitted by `RequestIdMiddleware` and include:

- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

The middleware propagates an inbound `X-Request-ID` header when supplied. If no request ID is supplied, it generates one and adds it to the response. The same request ID is included in the completion log.

## Data model

The initial PostgreSQL schema contains three tables:

```text
workspaces
  id UUID primary key
  name text, unique, required
  created_at timestamptz, required
  updated_at timestamptz, required

usage_samples
  id UUID primary key
  workspace_id UUID foreign key -> workspaces.id, cascade delete
  provider text, required
  region text, required
  resource_type text, required
  usage_amount numeric(18, 6), required
  usage_unit text, required
  measured_at timestamptz, required
  created_at timestamptz, required

carbon_intensity_samples
  id UUID primary key
  region text, indexed, required
  measured_at timestamptz, indexed, required
  grams_co2e_per_kwh numeric(12, 4), required
  source text, required
  created_at timestamptz, required
```

Only the workspace repository exists in T004. It supports creating, listing, and fetching workspaces using an externally managed async SQLAlchemy session. Route handlers do not perform direct database access.

## Local infrastructure

```text
docker-compose.yml
  api                  FastAPI/Uvicorn container exposed on host port 8000
  postgres             PostgreSQL container exposed on host port 5432
  redis                Redis container exposed on host port 6379
```

The API container runs as a non-root user and has a container health check that calls `GET /healthz`. PostgreSQL and Redis have image-native health checks. Alembic migrations use `CARBON_API_DATABASE_URL`.

## Dependency direction

The project follows this dependency direction as features are added:

```text
routes -> schemas -> services -> repositories/clients -> database/cache/external APIs
```

Current persistence follows that boundary by keeping SQLAlchemy access inside repositories and database helper modules. No route handler imports SQLAlchemy or performs persistence work.

## API surface

- `GET /healthz` returns a JSON liveness payload and an `X-Request-ID` response header.

FastAPI documentation and OpenAPI routes are disabled by default so the only default exposed endpoint is `/healthz`.
