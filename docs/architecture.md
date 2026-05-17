# Architecture

## Current scope

T006 provides the FastAPI application, a liveness endpoint, environment-backed configuration, structured JSON request logging, request ID middleware, Docker support for local development, initial PostgreSQL persistence, workspace create/list/fetch endpoints, and a deterministic carbon calculation service. Persistence includes SQLAlchemy models, Alembic migrations, async database/session helpers, and a workspace repository behind a workspace service.

Redis is still infrastructure only. The application intentionally does not include Redis application code, usage ingestion, reporting, authentication, metrics, or external API clients yet. The carbon calculation service is available to application services but is not exposed through an HTTP endpoint yet.

## Package layout

```text
src/carbon_platform_api/
  config.py                         Pydantic settings loaded from CARBON_API_* variables
  logging.py                        Standard-library JSON logging formatter/configuration
  main.py                           FastAPI app factory and ASGI app
  dependencies.py                   FastAPI dependency wiring for sessions/services
  db/base.py                        SQLAlchemy declarative base and naming convention
  db/session.py                     Async SQLAlchemy engine/session factory helpers
  middleware/request_id.py          Request ID response header and completion logging
  models/                           SQLAlchemy persistence models
  repositories/workspaces.py        Workspace repository using an async SQLAlchemy session
  routes/health.py                  HTTP route for GET /healthz
  routes/workspaces.py              HTTP routes for workspace create/list/fetch
  schemas/carbon_calculations.py    Calculation input/output schemas and enums
  schemas/health.py                 Response schema for the health endpoint
  schemas/workspaces.py             Request/response schemas for workspace endpoints
  services/carbon_calculations.py   Carbon calculation service and provider protocols
  services/workspaces.py            Workspace business service and repository protocol
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

The workspace repository supports creating, listing, fetching by ID, and fetching by name using an externally managed async SQLAlchemy session. It returns repository data records rather than leaking SQLAlchemy models to route handlers.

The workspace service depends on a small repository protocol. It normalizes workspace names, validates duplicate names before create, and translates missing workspaces into service-level errors. Route handlers perform HTTP concerns only: request/response schema handling and translating service errors to `409 Conflict` or `404 Not Found`.

## Carbon calculation flow

`carbon_platform_api.schemas.carbon_calculations` defines the calculation input and output shapes plus supported demo resource and usage-unit enums. `carbon_platform_api.services.carbon_calculations.CarbonCalculationService` calculates emissions using this flow:

```text
CarbonCalculationInput
  -> validate positive usage, non-negative carbon intensity, and non-blank region
  -> load a resource/region energy factor from EnergyFactorProviderProtocol
  -> convert usage to the factor's normalized unit through UsageUnitConverterProtocol
  -> energy_kwh = normalized_usage_amount * kwh_per_normalized_unit
  -> estimated_grams_co2e = energy_kwh * carbon_intensity_grams_co2e_per_kwh
  -> round normalized usage and kWh to 6 decimal places, grams CO2e to 4 decimal places
```

The default providers use deliberately simple public-safe demo factors:

| Resource type | Normalized unit | Demo kWh per normalized unit |
| --- | --- | ---: |
| `vcpu` | `vcpu_hour` | `0.0500` |
| `memory` | `gb_hour` | `0.0005` |
| `storage` | `gb_month` | `0.0001` |
| `network` | `gb` | `0.0020` |

Supported demo unit conversions include `vcpu_minute` to `vcpu_hour`, `gb_minute` to `gb_hour`, `tb_month` to `gb_month`, and `mb`/`tb` to `gb`. These factors and conversions are sample values for deterministic portfolio behaviour only; they are not authoritative energy or emissions measurements.

Extension points are intentionally small. Future factor sources can implement `EnergyFactorProviderProtocol`, which receives resource type and region, and future unit conversion strategies can implement `UsageUnitConverterProtocol`, without changing route handlers, repositories, or the core calculation formula. The default demo factors are region-independent. The service accepts carbon intensity as an input value in grams CO2e/kWh and does not fetch external carbon intensity data or use Redis.

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

Current persistence follows that boundary by keeping SQLAlchemy access inside repositories and database helper modules. Workspace routes depend on schemas and the workspace service, while FastAPI dependency wiring constructs the concrete async session and repository. No route handler imports SQLAlchemy or performs persistence work. `scripts/check-layering.py` is part of the quality gate and fails if route modules import SQLAlchemy, Alembic, database/session modules, models, or repositories directly.

## Automation guardrails

The full quality gate includes two repository safety checks:

- `scripts/check-no-private-terms.py` scans repository text files for obvious private markers, non-public hostnames, and secret-like tokens. `CARBON_API_PRIVATE_TERMS` can add a comma-separated custom denylist.
- `scripts/check-layering.py` enforces the route-to-service boundary described above.

`scripts/build-loop.sh` requires the agent prompt to select the lowest-numbered TODO or IN_PROGRESS ticket and performs clean-tree/upstream checks before each autonomous cycle.

## API surface

- `GET /healthz` returns a JSON liveness payload and an `X-Request-ID` response header.
- `POST /workspaces` accepts `{"name":"Demo Workspace"}` and returns the created workspace with `id`, `name`, `created_at`, and `updated_at`.
- `GET /workspaces` returns a JSON array of workspaces.
- `GET /workspaces/{workspace_id}` returns one workspace by UUID.

Workspace names must be non-blank, at most 120 characters, and unique. Duplicate names return `409 Conflict`; missing workspace IDs return `404 Not Found`.

No HTTP endpoint exposes carbon calculation yet; the service is available for future usage ingestion work.

FastAPI documentation and OpenAPI routes are disabled by default. They are exposed only when `CARBON_API_DOCS_ENABLED=true`.
