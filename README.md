# carbon-platform-api

carbon-platform-api is an independent public portfolio project demonstrating backend and platform engineering with Python, FastAPI, PostgreSQL, Redis, Docker Compose, Prometheus, Grafana, structured logging, health/readiness checks, tests, and CI.

The API tracks public-safe sample compute usage, calculates deterministic demo carbon estimates, persists usage samples, and exposes basic summary reports. It is intentionally a portfolio/demo service, not an authoritative carbon accounting product.

## Public-safety constraints

This repository uses only public-safe sample code, fake data, and local placeholder configuration. Do not add employer code, private data, non-public URLs or hostnames, credentials, screenshots, diagrams, or architecture. The project must not imply endorsement by any employer or organization.

## Implemented scope

Current implemented capabilities:

- Python 3.12 FastAPI application using a `src/` layout.
- Environment-backed settings loaded from `CARBON_API_*` variables.
- Structured JSON request logging with `X-Request-ID` propagation.
- Lightweight liveness, dependency readiness, and Prometheus metrics endpoints.
- Async SQLAlchemy persistence, Alembic migrations, and repository boundaries.
- Workspace create/list/fetch endpoints.
- Usage sample ingestion with persisted demo emissions estimates.
- Summary reporting across all workspaces or one workspace.
- Mockable carbon intensity HTTP client and Redis cache abstractions.
- Docker Compose local stack for API, PostgreSQL, Redis, Prometheus, and Grafana.
- Public-safe GitHub Actions CI for linting, formatting, type checks, tests, migrations, and Compose validation.

Out of scope today: authentication, deployment infrastructure, hosted monitoring integrations, tracing, direct HTTP carbon-intensity lookup, and production-grade carbon factors.

## Requirements

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/) for dependency management and command execution
- `make`
- Docker with Docker Compose v2 for the local container stack

## Quick start with Docker

Copy the safe local defaults if you want a `.env` file:

```sh
cp example.env .env
```

Validate, build, and start the full local stack:

```sh
docker compose config
docker compose build
docker compose up --detach
```

Apply database migrations before using workspace, usage ingestion, or reporting endpoints:

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

Check the API and local observability services:

```sh
curl -i http://localhost:8000/healthz
curl -i http://localhost:8000/readyz
curl -i http://localhost:8000/metrics
curl -i http://localhost:9090/-/healthy
curl -i http://localhost:3000/api/health
```

Stop and remove local containers, networks, and volumes:

```sh
docker compose down --volumes --remove-orphans
```

For a longer fake-data flow, see [Sample API walkthrough](docs/api-walkthrough.md).

## Run locally without Docker

Install dependencies:

```sh
make install
```

Start the API process:

```sh
make run
```

`GET /healthz` works without PostgreSQL or Redis. `GET /readyz` and business endpoints require reachable PostgreSQL/Redis settings, and business endpoints require Alembic migrations to be applied.

## Configuration

Application settings are loaded from environment variables with the `CARBON_API_` prefix.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CARBON_API_APP_NAME` | `carbon-platform-api` | FastAPI application name. |
| `CARBON_API_APP_VERSION` | `0.1.0` | FastAPI application version. |
| `CARBON_API_ENVIRONMENT` | `local` | Runtime environment label. |
| `CARBON_API_LOG_LEVEL` | `INFO` | Standard library log level for structured JSON logs. |
| `CARBON_API_DOCS_ENABLED` | `false` | Enables `/docs`, `/redoc`, and `/openapi.json` only when set to `true`. |
| `CARBON_API_DATABASE_URL` | `postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api` | Async SQLAlchemy PostgreSQL URL. |
| `CARBON_API_REDIS_URL` | `redis://localhost:6379/0` | Redis URL used by cache implementations and readiness checks. |
| `CARBON_API_CARBON_INTENSITY_PROVIDER_BASE_URL` | `https://carbon-intensity.example.invalid` | Public-safe placeholder base URL for the carbon intensity provider client. |
| `CARBON_API_CARBON_INTENSITY_PROVIDER_TIMEOUT_SECONDS` | `2.0` | Timeout, in seconds, for carbon intensity provider HTTP calls. |
| `CARBON_API_CARBON_INTENSITY_CACHE_TTL_SECONDS` | `900` | Redis cache TTL, in seconds, for successful carbon intensity provider responses. |

FastAPI docs and OpenAPI routes are disabled by default. Enable them only for local exploration:

```sh
CARBON_API_DOCS_ENABLED=true make run
```

## API surface

| Method and path | Purpose |
| --- | --- |
| `GET /healthz` | Lightweight liveness check. Returns `{"status":"ok"}` and an `X-Request-ID` header. |
| `GET /readyz` | Checks PostgreSQL and Redis dependency connectivity. |
| `GET /metrics` | Returns Prometheus text exposition metrics. |
| `POST /workspaces` | Creates a workspace with a unique public-safe name. |
| `GET /workspaces` | Lists workspaces. |
| `GET /workspaces/{workspace_id}` | Fetches one workspace by UUID. |
| `POST /workspaces/{workspace_id}/usage-samples` | Ingests one usage sample and stores calculated demo emissions fields. |
| `GET /workspaces/{workspace_id}/reports/summary` | Returns summary totals for one workspace. |
| `GET /reports/summary` | Returns summary totals across all workspaces. |

If a request supplies `X-Request-ID`, the API propagates it to the response and completion log. Otherwise, the API generates one.

## Database migrations

Start PostgreSQL, then apply migrations from the host:

```sh
docker compose up --detach postgres
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

Roll back all local migrations:

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic downgrade base
```

The API does not auto-run migrations at startup.

## Workspace API examples

Create a workspace:

```sh
curl -i \
  -X POST http://127.0.0.1:8000/workspaces \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo Workspace"}'
```

List workspaces:

```sh
curl -i http://127.0.0.1:8000/workspaces
```

Fetch one workspace, replacing the UUID with a value returned by create/list:

```sh
curl -i http://127.0.0.1:8000/workspaces/00000000-0000-0000-0000-000000000000
```

Duplicate workspace names return `409 Conflict`. Missing workspace IDs return `404 Not Found`.

## Usage sample ingestion example

Ingest one fake compute usage sample for an existing workspace:

```sh
curl -i \
  -X POST http://127.0.0.1:8000/workspaces/00000000-0000-0000-0000-000000000000/usage-samples \
  -H 'Content-Type: application/json' \
  -d '{
    "provider":"sample-cloud",
    "region":"sample-region-1",
    "resource_type":"vcpu",
    "usage_amount":"10",
    "usage_unit":"vcpu_hour",
    "measured_at":"2026-01-01T12:00:00Z",
    "carbon_intensity_grams_co2e_per_kwh":"400"
  }'
```

Supported `resource_type` values are `vcpu`, `memory`, `storage`, and `network`. Supported `usage_unit` values are `vcpu_hour`, `vcpu_minute`, `gb_hour`, `gb_minute`, `gb_month`, `tb_month`, `gb`, `mb`, and `tb`; not every unit is compatible with every resource type.

The endpoint returns the persisted sample with calculated `normalized_usage_amount`, `normalized_usage_unit`, `energy_kwh`, `estimated_grams_co2e`, and `factor_source` fields. Missing workspaces return `404 Not Found`; incompatible resource/unit pairs return `422 Unprocessable Content`.

## Reporting API examples

Fetch a summary for one workspace:

```sh
curl -i \
  'http://127.0.0.1:8000/workspaces/00000000-0000-0000-0000-000000000000/reports/summary?start_time=2026-01-01T00:00:00Z&end_time=2026-02-01T00:00:00Z'
```

Fetch a summary across all workspaces:

```sh
curl -i \
  'http://127.0.0.1:8000/reports/summary?start_time=2026-01-01T00:00:00Z&end_time=2026-02-01T00:00:00Z'
```

Report responses include the applied `time_range`, an overall `total`, and totals grouped in `by_workspace`, `by_provider`, and `by_region`. `start_time` is inclusive and `end_time` is exclusive. Supplied timestamps must be timezone-aware. Invalid ranges return `422 Unprocessable Content`; missing workspace-scoped reports return `404 Not Found`; empty reports return zero totals with empty groups.

## Observability

Readiness checks PostgreSQL and Redis connectivity without requiring database migrations:

```sh
curl -i http://127.0.0.1:8000/readyz
```

Healthy response body:

```json
{"status":"ready","dependencies":[{"name":"database","status":"ok"},{"name":"redis","status":"ok"}]}
```

Metrics are exposed in Prometheus text format:

```sh
curl -i http://127.0.0.1:8000/metrics
```

The output includes Python process metrics plus `carbon_api_http_requests_total` and `carbon_api_http_request_duration_seconds` labeled by method, route path, and status code.

Docker Compose includes local Prometheus at `http://localhost:9090` and Grafana at `http://localhost:3000`. Prometheus scrapes `api:8000/metrics` inside the Compose network. Grafana provisions a Prometheus datasource and the `Carbon Platform API Local Overview` dashboard. Log in with the safe local placeholder values `local_admin` / `local_dev_password` unless overridden in `.env`.

## Development commands

Repository tests require PostgreSQL. Start it first or use the full quality gate, which starts an isolated PostgreSQL service automatically.

```sh
docker compose up --detach postgres
make test
make lint
make typecheck
```

Run the full project gate:

```sh
scripts/quality-gate.sh
```

The quality gate runs shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, Docker Compose config validation, Alembic migrations, and pytest with coverage. Carbon intensity client tests use fakes and `httpx.MockTransport`; they do not call a live third-party API.

## CI contract

GitHub Actions runs the `CI` workflow on pull requests and pushes to the default `main` branch. It uses public-safe local PostgreSQL service credentials for integration tests, caches `uv` dependencies from `uv.lock`, and runs the same substantive checks as the local quality gate. The workflow does not require repository secrets, upload coverage, run deployment jobs, or call external carbon providers.

## Automation build loop

`scripts/build-loop.sh` runs bounded pi build cycles. It requires a clean working tree, pulls with `git pull --ff-only` when the branch has an upstream, refuses to start while ahead of upstream unless `--allow-ahead` or `PI_BUILD_ALLOW_AHEAD=1` is set, and stops if the upstream changes during a cycle.

## Known limitations

- The API does not auto-run Alembic migrations at startup.
- Carbon calculation factors and conversions are public-safe demo values only, not authoritative measurements.
- Usage ingestion requires caller-supplied carbon intensity values; it does not call the carbon intensity provider or Redis cache.
- Direct carbon intensity lookup is implemented behind service/client/cache abstractions but is not exposed through HTTP.
- Redis cache code exists, but current business endpoints do not use it yet.
- Reporting uses simple aggregate queries only; there are no time buckets, rollups, pagination, or materialized summaries.
- Authentication and authorization are not included yet.
- FastAPI docs/OpenAPI routes are disabled by default.
- Prometheus and Grafana are local Docker Compose services for metrics exploration only.
- No hosted monitoring integration, tracing integration, deployment automation, or secret-management integration is configured.

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [Sample API walkthrough](docs/api-walkthrough.md)
- [ADR 0001: Project scope](docs/adr/0001-project-scope.md)
- [ADR 0002: Layered architecture and mockable boundaries](docs/adr/0002-layered-architecture-and-mockable-boundaries.md)
- [ADR 0003: Async PostgreSQL persistence and local Docker stack](docs/adr/0003-async-postgresql-and-local-docker-stack.md)
- [ADR 0004: Demo carbon calculation and cache-first intensity lookup](docs/adr/0004-demo-carbon-calculation-and-cache-first-intensity.md)
- [ADR 0005: Observability and quality guardrails](docs/adr/0005-observability-and-quality-guardrails.md)
