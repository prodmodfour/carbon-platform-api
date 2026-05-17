# Architecture

## Purpose and scope

carbon-platform-api is a public-safe portfolio API for tracking fake/sample compute usage and deterministic demo carbon estimates. It demonstrates production-style backend boundaries without using employer systems, private data, private hostnames, credentials, or non-public architecture.

Implemented scope:

- FastAPI application with request ID middleware and structured JSON logs.
- `GET /healthz`, `GET /readyz`, and `GET /metrics` operational endpoints.
- Async SQLAlchemy persistence with Alembic migrations.
- Workspace create/list/fetch endpoints.
- Usage sample ingestion with persisted demo emissions estimates.
- Summary reporting grouped by workspace, provider, and region.
- Optional API key authentication for business endpoints.
- Mockable carbon calculation, carbon intensity client, and Redis cache services.
- Docker Compose local stack for API, PostgreSQL, Redis, Prometheus, and Grafana.
- Local quality gate and GitHub Actions CI.
- Cloud-neutral deployment guidance without deployment automation or IaC files.

Intentionally excluded today: OAuth, user accounts, password storage, deployment automation/IaC, hosted monitoring integrations, tracing, direct HTTP carbon-intensity lookup, and authoritative carbon accounting factors.

## System context

```text
Developer or API caller
  -> FastAPI app on port 8000, optionally with X-API-Key for business endpoints
      -> PostgreSQL for workspaces, usage samples, and reporting reads
      -> Redis for carbon intensity cache and readiness checks
      -> optional external carbon intensity provider through a mockable client
  -> Prometheus on port 9090 scrapes FastAPI /metrics in Docker Compose
  -> Grafana on port 3000 reads Prometheus through provisioned local datasource
```

The external carbon intensity provider default is `https://carbon-intensity.example.invalid`, a reserved public-safe placeholder. Tests use fakes or `httpx.MockTransport`; they do not depend on a live third-party service.

## Dependency direction

The required dependency direction is:

```text
routes -> schemas -> services -> repositories/clients -> database/cache/external APIs
```

Concrete boundary rules:

- Route handlers handle HTTP details only: request parsing, dependency injection, response schemas, and HTTP error translation.
- Schemas define public request/response/value-object shapes.
- Services own business rules, validation that spans fields/resources, and orchestration.
- Repositories own SQLAlchemy queries and persistence mapping.
- Clients own external HTTP calls.
- Cache modules own Redis serialization and commands.
- Database/session helpers own SQLAlchemy engine and session creation.

`scripts/check-layering.py` enforces the most important route boundary by failing if route modules import SQLAlchemy, Alembic, database/session modules, models, or repositories directly.

## Package layout

```text
src/carbon_platform_api/
  config.py                         Pydantic settings loaded from CARBON_API_* variables
  logging.py                        Standard-library JSON logging formatter/configuration
  metrics.py                        Prometheus registry and HTTP metrics recorders
  main.py                           FastAPI app factory and ASGI app
  dependencies.py                   FastAPI dependency wiring for auth, sessions, and services
  cache/carbon_intensity.py         Redis cache protocol/implementation for intensity samples
  cache/health.py                   Redis readiness check protocol/implementation
  clients/carbon_intensity.py       HTTP provider client protocol/implementation
  db/base.py                        SQLAlchemy declarative base and naming convention
  db/health.py                      PostgreSQL readiness check implementation
  db/session.py                     Async SQLAlchemy engine/session factory helpers
  middleware/metrics.py             HTTP request metrics middleware
  middleware/request_id.py          Request ID response header and completion logging
  models/                           SQLAlchemy persistence models
  repositories/reports.py           Read-only reporting aggregate queries
  repositories/usage_samples.py     Usage sample persistence
  repositories/workspaces.py        Workspace persistence
  routes/health.py                  HTTP route for GET /healthz
  routes/observability.py           HTTP routes for GET /readyz and GET /metrics
  routes/reports.py                 HTTP routes for summary reports
  routes/workspaces.py              HTTP routes for workspaces and usage ingestion
  schemas/carbon_calculations.py    Calculation input/output schemas and enums
  schemas/carbon_intensity.py       Carbon intensity query/sample value objects
  schemas/health.py                 Response schema for health
  schemas/observability.py          Response schemas for readiness
  schemas/reports.py                Response schemas for summary reports
  schemas/usage_samples.py          Request/response schemas for usage ingestion
  schemas/workspaces.py             Request/response schemas for workspaces
  services/auth.py                  API key authentication service
  services/carbon_calculations.py   Carbon calculation service and provider protocols
  services/carbon_intensity.py      Cache-first carbon intensity lookup service
  services/metrics.py               Prometheus text rendering service
  services/readiness.py             Dependency readiness coordination service
  services/reporting.py             Report validation and repository coordination
  services/usage_ingestion.py       Usage validation/calculation/persistence orchestration
  services/workspaces.py            Workspace business service and repository protocol
alembic/
  env.py                            Async Alembic migration environment
  versions/                         Database schema migrations
observability/
  prometheus/prometheus.yml         Local scrape config for api:8000/metrics
  grafana/                          Local datasource, dashboard provider, and dashboard JSON
```

## Runtime assembly

```text
create_app(settings)
  -> configure JSON logging
  -> build SQLAlchemy async engine and session factory
  -> build Redis client
  -> build isolated Prometheus registry
  -> read API key auth settings for request dependencies
  -> install metrics middleware
  -> install request ID middleware
  -> include health, observability, workspace, and report routers
```

FastAPI dependency functions in `dependencies.py` construct per-request service instances with concrete repositories/checks. The routes depend on services, not on repositories or database sessions directly.

## Configuration

Application configuration is centralized in `carbon_platform_api.config.Settings` and loaded from environment variables with the `CARBON_API_` prefix.

Current settings:

- `app_name`
- `app_version`
- `environment`
- `log_level`
- `docs_enabled`
- `auth_enabled`
- `auth_api_keys`
- `database_url`
- `redis_url`
- `carbon_intensity_provider_base_url`
- `carbon_intensity_provider_timeout_seconds`
- `carbon_intensity_cache_ttl_seconds`

FastAPI documentation and OpenAPI routes are disabled by default. They are only exposed when `CARBON_API_DOCS_ENABLED=true`.

## API key authentication

`ApiKeyAuthService` validates opaque API keys supplied through the `X-API-Key` header. The service depends only on configured settings values, uses constant-time comparisons through the standard library, and does not log API key values.

Authentication is disabled by default for local exploration. When `CARBON_API_AUTH_ENABLED=true`, route-level dependencies require a configured API key before business endpoint handlers run. Missing or invalid keys return `401 Unauthorized` with a generic error.

Protected business endpoints:

```text
POST /workspaces
GET /workspaces
GET /workspaces/{workspace_id}
POST /workspaces/{workspace_id}/usage-samples
GET /workspaces/{workspace_id}/reports/summary
GET /reports/summary
```

`GET /healthz`, `GET /readyz`, and `GET /metrics` intentionally remain unprotected so liveness checks, dependency readiness checks, and Prometheus scraping can work without credentials. FastAPI docs remain controlled separately by `docs_enabled`.

## Logging and request correlation

`carbon_platform_api.logging` configures standard-library JSON logs. `RequestIdMiddleware` propagates an inbound `X-Request-ID` header when supplied; otherwise it generates one. The response always includes `X-Request-ID`.

Request completion logs include:

- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

Readiness failure logs include the dependency name and exception type only. They avoid connection URLs, credentials, raw environment dumps, and secret-like values.

## Observability endpoints

```text
GET /healthz
  -> route returns {"status":"ok"}
  -> does not touch PostgreSQL or Redis

GET /readyz
  -> route calls ReadinessService
  -> service runs DatabaseReadinessCheck and RedisReadinessCheck
  -> route returns 200 when all dependencies are ok, otherwise 503

GET /metrics
  -> route calls MetricsService
  -> service renders Prometheus text from the app's isolated registry
```

The Prometheus registry includes process metrics and API request metrics recorded by `RequestMetricsMiddleware`:

- `carbon_api_http_requests_total`
- `carbon_api_http_request_duration_seconds`

HTTP metrics are labeled by method, matched route path, and status code. Dynamic route templates are used when available to avoid high-cardinality UUID labels.

## API surface

```text
GET /healthz
GET /readyz
GET /metrics
POST /workspaces
GET /workspaces
GET /workspaces/{workspace_id}
POST /workspaces/{workspace_id}/usage-samples
GET /workspaces/{workspace_id}/reports/summary
GET /reports/summary
```

FastAPI docs/OpenAPI routes are disabled by default and are only exposed when `CARBON_API_DOCS_ENABLED=true`. Business endpoints require `X-API-Key` when `CARBON_API_AUTH_ENABLED=true`; operational endpoints remain unprotected.

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

`carbon_intensity_samples` is present for future persistence use. Current carbon intensity provider/cache logic stores successful provider responses in Redis, and current usage ingestion accepts caller-supplied carbon intensity values.

## Workspace flow

```text
POST /workspaces
  -> require_api_key validates X-API-Key when auth is enabled
  -> WorkspaceCreateRequest validates name shape
  -> WorkspaceService strips and validates business uniqueness
  -> WorkspaceRepository reads/writes workspaces table
  -> route returns WorkspaceResponse or 409 Conflict

GET /workspaces
  -> require_api_key validates X-API-Key when auth is enabled
  -> WorkspaceService lists workspaces
  -> WorkspaceRepository reads workspaces table
  -> route returns list[WorkspaceResponse]

GET /workspaces/{workspace_id}
  -> require_api_key validates X-API-Key when auth is enabled
  -> WorkspaceService fetches by UUID
  -> WorkspaceRepository reads workspaces table
  -> route returns WorkspaceResponse or 404 Not Found
```

Workspace names must be non-blank, at most 120 characters, and unique.

## Usage ingestion flow

```text
POST /workspaces/{workspace_id}/usage-samples
  -> require_api_key validates X-API-Key when auth is enabled
  -> UsageSampleIngestionRequest validates shape, positive usage, timezone-aware measured_at, and non-negative carbon intensity
  -> UsageIngestionService verifies workspace existence through a workspace lookup protocol
  -> UsageIngestionService calls CarbonCalculationProtocol
  -> UsageSampleRepository persists raw and calculated fields
  -> route returns UsageSampleResponse
```

Missing workspaces become `404 Not Found`. Incompatible resource/unit pairs become `422 Unprocessable Content`. Usage ingestion currently does not fetch carbon intensity values from the provider/cache service.

## Reporting flow

`ReportSummaryResponse` has this public shape:

```text
ReportSummaryResponse
  time_range              start_time/end_time filters echoed back to the caller
  total                   overall sample count, kWh, and estimated grams CO2e
  by_workspace            totals grouped by workspace ID and name
  by_provider             totals grouped by provider label
  by_region               totals grouped by region label
```

Report request flow:

```text
GET /reports/summary or /workspaces/{workspace_id}/reports/summary
  -> require_api_key validates X-API-Key when auth is enabled
  -> route parses optional start_time/end_time query parameters
  -> ReportingService validates timezone awareness and range order
  -> ReportingService verifies workspace existence for workspace-scoped reports
  -> ReportingRepository runs aggregate SQLAlchemy queries
  -> route serializes ReportSummaryResponse
```

Filtering semantics are deterministic:

- `start_time` is an inclusive `usage_samples.measured_at` lower bound.
- `end_time` is an exclusive `usage_samples.measured_at` upper bound.
- omitted bounds are unbounded.
- empty reports return zero totals and empty grouping arrays.

## Carbon calculation flow

`CarbonCalculationService` calculates emissions with public-safe demo values:

```text
CarbonCalculationInput
  -> validate positive usage, non-negative carbon intensity, and non-blank region
  -> load a resource/region energy factor from EnergyFactorProviderProtocol
  -> convert usage to the factor's normalized unit through UsageUnitConverterProtocol
  -> energy_kwh = normalized_usage_amount * kwh_per_normalized_unit
  -> estimated_grams_co2e = energy_kwh * carbon_intensity_grams_co2e_per_kwh
  -> round normalized usage and kWh to 6 decimal places, grams CO2e to 4 decimal places
```

Default demo factors:

| Resource type | Normalized unit | Demo kWh per normalized unit |
| --- | --- | ---: |
| `vcpu` | `vcpu_hour` | `0.0500` |
| `memory` | `gb_hour` | `0.0005` |
| `storage` | `gb_month` | `0.0001` |
| `network` | `gb` | `0.0020` |

Supported demo unit conversions include `vcpu_minute` to `vcpu_hour`, `gb_minute` to `gb_hour`, `tb_month` to `gb_month`, and `mb`/`tb` to `gb`. These factors and conversions are deterministic demo values only; they are not authoritative energy or emissions measurements.

Extension points are intentionally small. Future factor sources can implement `EnergyFactorProviderProtocol`, and future unit conversion strategies can implement `UsageUnitConverterProtocol`, without changing route handlers, repositories, or the core calculation formula.

## Carbon intensity client/cache flow

`CarbonIntensityService` depends on two protocols:

```text
CarbonIntensityService
  -> CarbonIntensityCacheProtocol.get(query)
  -> return cached sample on hit
  -> CarbonIntensityClientProtocol.fetch_intensity(query) on miss
  -> CarbonIntensityCacheProtocol.set(query, sample, ttl) after successful provider response
```

`HttpCarbonIntensityClient` performs HTTP `GET /intensity` requests with `region`, `start_time`, and `end_time` query parameters. It translates provider timeouts/failures into client-level exceptions and validates response JSON into `CarbonIntensitySample`.

`RedisCarbonIntensityCache` serializes samples as JSON and stores them under deterministic keys with a positive TTL. Only successful provider responses are cached. Invalid cached payloads raise a cache serialization error rather than silently returning incorrect data.

## Local infrastructure

```text
docker-compose.yml
  api                  FastAPI/Uvicorn container exposed on host port 8000
  postgres             PostgreSQL container exposed on host port 5432
  redis                Redis container exposed on host port 6379
  prometheus           Prometheus server exposed on host port 9090
  grafana              Grafana server exposed on host port 3000
```

The API container runs as a non-root user and has a container health check against `GET /healthz`. PostgreSQL and Redis have image-native health checks. Prometheus scrapes the API at `api:8000/metrics` inside the Compose network. Grafana provisions a local Prometheus datasource and dashboard from repository files. Grafana placeholder credentials are local-only and not production credentials.

## Deployment guidance

[Deployment guide](deployment.md) documents a public-safe, cloud-neutral release path for a containerized API, PostgreSQL, Redis, health/readiness probes, metrics scraping, explicit Alembic migrations, rollback planning, and operational risks. It intentionally does not introduce deployment automation, real cloud accounts, real hostnames, credentials, secret-management integration, or IaC files.

## Quality gate and CI

Local quality gate flow:

```text
scripts/quality-gate.sh
  -> shell syntax checks
  -> public-safety term scan
  -> route-layering check
  -> Ruff lint
  -> Ruff format check
  -> mypy strict type check
  -> docker compose config
  -> isolated PostgreSQL startup
  -> alembic upgrade head
  -> pytest with coverage
  -> cleanup isolated PostgreSQL volume
```

GitHub Actions runs the same substantive checks on pull requests and pushes to `main`. CI uses public-safe local PostgreSQL service credentials, requires no repository secrets, and does not deploy artifacts.

## Known limitations

- Alembic migrations must be run explicitly before business endpoints are used.
- Carbon calculation factors are demo values only.
- Usage ingestion requires caller-supplied carbon intensity values.
- Direct carbon intensity lookup is not exposed through HTTP.
- Redis cache code is implemented but current business endpoints do not use it.
- Reports are simple aggregates without time buckets, rollups, pagination, or materialized summaries.
- API key auth is intentionally simple for portfolio demo use; there is no OAuth, user account model, password storage, key rotation, rate limiting, or role-based authorization.
- FastAPI docs/OpenAPI routes are disabled by default.
- Prometheus and Grafana are local-only Compose services.
- Deployment guidance is documentation only; no tracing, hosted monitoring, deployment automation, IaC, or secret-management integration is configured.
