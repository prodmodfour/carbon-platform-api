# Architecture

## Current scope

T009 provides the FastAPI application, a liveness endpoint, environment-backed configuration, structured JSON request logging, request ID middleware, Docker support for local development, PostgreSQL persistence, workspace create/list/fetch endpoints, usage sample ingestion with persisted calculated estimates, summary reporting endpoints, a deterministic carbon calculation service, and a mockable carbon intensity provider client with Redis-backed caching. Persistence includes SQLAlchemy models, Alembic migrations, async database/session helpers, workspace, usage sample, and reporting repositories, and services behind the HTTP routes.

The application intentionally does not include authentication, metrics, or HTTP endpoints for direct carbon intensity lookup. Carbon intensity provider access and Redis cache access are available to services through protocols and concrete implementations, but usage ingestion currently uses caller-supplied carbon intensity values rather than calling the provider.

## Package layout

```text
src/carbon_platform_api/
  config.py                         Pydantic settings loaded from CARBON_API_* variables
  logging.py                        Standard-library JSON logging formatter/configuration
  main.py                           FastAPI app factory and ASGI app
  dependencies.py                   FastAPI dependency wiring for sessions/services
  cache/carbon_intensity.py         Redis cache protocol/implementation for intensity samples
  clients/carbon_intensity.py       HTTP provider client protocol/implementation
  db/base.py                        SQLAlchemy declarative base and naming convention
  db/session.py                     Async SQLAlchemy engine/session factory helpers
  middleware/request_id.py          Request ID response header and completion logging
  models/                           SQLAlchemy persistence models
  repositories/reports.py           Read-only reporting aggregates using an async SQLAlchemy session
  repositories/usage_samples.py     Usage sample repository using an async SQLAlchemy session
  repositories/workspaces.py        Workspace repository using an async SQLAlchemy session
  routes/health.py                  HTTP route for GET /healthz
  routes/reports.py                 HTTP routes for summary reports
  routes/workspaces.py              HTTP routes for workspace create/list/fetch and usage ingestion
  schemas/carbon_calculations.py    Calculation input/output schemas and enums
  schemas/carbon_intensity.py       Carbon intensity query/sample value objects
  schemas/health.py                 Response schema for the health endpoint
  schemas/reports.py                Response schemas for summary reports
  schemas/usage_samples.py          Request/response schemas for usage ingestion
  schemas/workspaces.py             Request/response schemas for workspace endpoints
  services/carbon_calculations.py   Carbon calculation service and provider protocols
  services/carbon_intensity.py      Cache-first carbon intensity lookup service
  services/reporting.py             Report input validation and repository coordination service
  services/usage_ingestion.py       Usage sample validation/calculation/persistence service
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
- `redis_url`
- `carbon_intensity_provider_base_url`
- `carbon_intensity_provider_timeout_seconds`
- `carbon_intensity_cache_ttl_seconds`

FastAPI documentation and OpenAPI routes remain disabled by default. They are only exposed when `CARBON_API_DOCS_ENABLED=true`. The default carbon intensity provider URL uses the reserved `.invalid` top-level domain so local development and tests do not accidentally depend on a live provider.

## Logging and request correlation

`carbon_platform_api.logging` configures a standard-library JSON log formatter. Request completion logs are emitted by `RequestIdMiddleware` and include:

- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

The middleware propagates an inbound `X-Request-ID` header when supplied. If no request ID is supplied, it generates one and adds it to the response. The same request ID is included in the completion log.

## Data model

The PostgreSQL schema contains three tables:

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
  normalized_usage_amount numeric(18, 6), required
  normalized_usage_unit text, required
  energy_kwh numeric(18, 6), required
  carbon_intensity_grams_co2e_per_kwh numeric(12, 4), required
  estimated_grams_co2e numeric(18, 4), required
  factor_source text, required
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

The usage sample repository persists raw usage fields together with calculated estimate fields using an externally managed async SQLAlchemy session. `UsageIngestionService` depends on small protocols for workspace lookup, usage sample persistence, and carbon calculation. Its ingestion flow is:

```text
UsageSampleIngestionRequest
  -> validate request shape, positive usage, timezone-aware measured_at, and non-negative carbon intensity
  -> verify workspace exists through the workspace repository protocol
  -> calculate normalized usage, kWh, and estimated grams CO2e through CarbonCalculationProtocol
  -> persist raw and calculated fields through the usage sample repository protocol
  -> return the persisted usage sample record to the route
```

Usage ingestion currently uses the carbon intensity value supplied in the request. It does not call the external carbon intensity provider or Redis cache. Missing workspaces become `404 Not Found`; incompatible resource/unit pairs become `422 Unprocessable Content`.

## Reporting flow

`carbon_platform_api.schemas.reports` defines the public summary response shape:

```text
ReportSummaryResponse
  time_range              start_time/end_time filters echoed back to the caller
  total                   overall sample count, kWh, and estimated grams CO2e
  by_workspace            totals grouped by workspace ID and name
  by_provider             totals grouped by provider label
  by_region               totals grouped by region label
```

`ReportingService` depends on small protocols for read-only report aggregation and workspace lookup. It validates that supplied time filters are timezone-aware and that `start_time` is before `end_time` when both are provided. Workspace-scoped reports verify workspace existence before querying aggregates. `ReportingRepository` owns the SQLAlchemy aggregate queries and returns repository records, keeping report route handlers free of database logic.

Report filtering semantics are intentionally simple and deterministic:

- `start_time` is an inclusive `usage_samples.measured_at` lower bound.
- `end_time` is an exclusive `usage_samples.measured_at` upper bound.
- omitted bounds are unbounded.
- empty reports return zero totals and empty grouping arrays.

The two reporting endpoints share the same service flow:

```text
GET /reports/summary or /workspaces/{workspace_id}/reports/summary
  -> parse optional start_time/end_time query parameters
  -> ReportingService validates time range and optional workspace existence
  -> ReportingRepository reads totals grouped by workspace, provider, and region
  -> route serializes ReportSummaryResponse
```

Invalid time ranges return `422 Unprocessable Content`; missing workspace-scoped reports return `404 Not Found`.

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

Extension points are intentionally small. Future factor sources can implement `EnergyFactorProviderProtocol`, which receives resource type and region, and future unit conversion strategies can implement `UsageUnitConverterProtocol`, without changing route handlers, repositories, or the core calculation formula. The default demo factors are region-independent. The service accepts carbon intensity as an input value in grams CO2e/kWh. Fetching carbon intensity values is a separate cache-first service described below.

## Carbon intensity client/cache flow

`carbon_platform_api.schemas.carbon_intensity` defines timezone-aware lookup windows and carbon intensity samples. `CarbonIntensityService` depends only on two small protocols:

```text
CarbonIntensityService
  -> CarbonIntensityCacheProtocol.get(query)
  -> return cached sample on hit
  -> CarbonIntensityClientProtocol.fetch_intensity(query) on miss
  -> CarbonIntensityCacheProtocol.set(query, sample, ttl) after successful provider response
```

`HttpCarbonIntensityClient` is the concrete external provider implementation. It performs HTTP `GET /intensity` requests with `region`, `start_time`, and `end_time` query parameters, translates timeouts and provider failures into client-level exceptions, and validates provider JSON into a `CarbonIntensitySample`. Tests inject `httpx.MockTransport`, so no live third-party provider is required.

`RedisCarbonIntensityCache` is the concrete cache implementation. Redis access is limited to a minimal command protocol with `get`, `set`, and `aclose`. Samples are serialized as JSON with Pydantic and stored under deterministic keys with a positive TTL from `CARBON_API_CARBON_INTENSITY_CACHE_TTL_SECONDS`. Only successful provider responses are cached; provider failures and timeouts are propagated and not stored. Invalid cached payloads raise a cache serialization error rather than silently returning incorrect data.

## Local infrastructure

```text
docker-compose.yml
  api                  FastAPI/Uvicorn container exposed on host port 8000
  postgres             PostgreSQL container exposed on host port 5432
  redis                Redis container exposed on host port 6379
```

The API container runs as a non-root user and has a container health check that calls `GET /healthz`. PostgreSQL and Redis have image-native health checks. Alembic migrations use `CARBON_API_DATABASE_URL`. Redis-backed cache code uses `CARBON_API_REDIS_URL` and defaults to `redis://redis:6379/0` in Docker Compose.

## Dependency direction

The project follows this dependency direction as features are added:

```text
routes -> schemas -> services -> repositories/clients -> database/cache/external APIs
```

Current persistence follows that boundary by keeping SQLAlchemy access inside repositories and database helper modules. Workspace, usage ingestion, and reporting routes depend on schemas and services, while FastAPI dependency wiring constructs the concrete async session and repositories. External HTTP access is isolated in `clients/`, and Redis access is isolated in `cache/`. No route handler imports SQLAlchemy, performs persistence work, calls external HTTP providers, or talks to Redis. `scripts/check-layering.py` is part of the quality gate and fails if route modules import SQLAlchemy, Alembic, database/session modules, models, or repositories directly.

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
- `POST /workspaces/{workspace_id}/usage-samples` accepts one compute usage sample and returns the persisted raw and calculated fields.
- `GET /workspaces/{workspace_id}/reports/summary` returns summary totals for one workspace.
- `GET /reports/summary` returns summary totals across all workspaces.

Workspace names must be non-blank, at most 120 characters, and unique. Duplicate names return `409 Conflict`; missing workspace IDs return `404 Not Found`.

Usage ingestion accepts `provider`, `region`, `resource_type`, `usage_amount`, `usage_unit`, `measured_at`, and `carbon_intensity_grams_co2e_per_kwh`. It stores calculated `normalized_usage_amount`, `normalized_usage_unit`, `energy_kwh`, `estimated_grams_co2e`, and `factor_source`. Incompatible resource/unit pairs return `422 Unprocessable Content`.

Reporting accepts optional `start_time` and `end_time` query parameters on both summary endpoints. Responses include an overall total and totals grouped by workspace, provider, and region. Time filters must be timezone-aware. `start_time` is inclusive, `end_time` is exclusive, and invalid ranges return `422 Unprocessable Content`.

No HTTP endpoint exposes direct carbon intensity lookup yet; that service is available for future flows.

FastAPI documentation and OpenAPI routes are disabled by default. They are exposed only when `CARBON_API_DOCS_ENABLED=true`.
