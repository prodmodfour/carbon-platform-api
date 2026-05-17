# carbon-platform-api

carbon-platform-api is an independent public portfolio project demonstrating backend and platform engineering with Python and FastAPI.

The long-term project goal is a production-style API for tracking compute-related carbon usage. The current scope includes a Python 3.12 FastAPI application, a liveness endpoint, environment-backed configuration, structured JSON request logging, request ID correlation, a Docker Compose local stack for the API, PostgreSQL, and Redis, PostgreSQL models/migrations, workspace create/list/fetch endpoints, usage sample ingestion with persisted calculated estimates, summary reporting endpoints, a deterministic carbon calculation service, and a mockable carbon intensity provider client with Redis-backed caching.

## Public-safety constraints

This repository uses only public-safe sample code and documentation. Do not add employer code, private data, internal URLs, hostnames, credentials, screenshots, diagrams, or architecture. The project must not imply endorsement by any employer or organization.

## Current API

- `GET /healthz` returns `{"status": "ok"}` and includes an `X-Request-ID` response header.
- `POST /workspaces` creates a workspace with a unique name.
- `GET /workspaces` lists workspaces.
- `GET /workspaces/{workspace_id}` fetches one workspace by UUID.
- `POST /workspaces/{workspace_id}/usage-samples` ingests one compute usage sample, calculates a demo emissions estimate from caller-supplied carbon intensity, and persists the raw and calculated fields.
- `GET /workspaces/{workspace_id}/reports/summary` returns usage and estimated-emissions totals for one workspace.
- `GET /reports/summary` returns usage and estimated-emissions totals across all workspaces.
- If a request supplies `X-Request-ID`, the same value is propagated to the response and request completion log. Otherwise, the API generates a request ID.

Workspace, usage ingestion, and reporting endpoints use SQLAlchemy through service/repository boundaries. Apply Alembic migrations before using them against a real database. The carbon calculation service uses documented public-safe demo factors and is called by usage ingestion. Carbon intensity provider calls and Redis access are isolated behind client/cache abstractions and are not exposed through HTTP endpoints yet. The application does not yet contain authentication or metrics.

## Requirements

- Python 3.12
- `uv` for dependency management and command execution
- `make`
- Docker with Docker Compose v2 for the local container stack

## Setup

```sh
make install
```

## Configuration

Application settings are loaded from environment variables with the `CARBON_API_` prefix.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CARBON_API_APP_NAME` | `carbon-platform-api` | FastAPI application name. |
| `CARBON_API_APP_VERSION` | `0.1.0` | FastAPI application version. |
| `CARBON_API_ENVIRONMENT` | `local` | Environment label included for runtime configuration. |
| `CARBON_API_LOG_LEVEL` | `INFO` | Standard library log level for structured JSON logs. |
| `CARBON_API_DOCS_ENABLED` | `false` | Enables `/docs`, `/redoc`, and `/openapi.json` only when set to `true`. |
| `CARBON_API_DATABASE_URL` | `postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api` | Async SQLAlchemy database URL for PostgreSQL. |
| `CARBON_API_REDIS_URL` | `redis://localhost:6379/0` | Redis URL used by cache implementations. Docker Compose sets this to `redis://redis:6379/0` for the API container. |
| `CARBON_API_CARBON_INTENSITY_PROVIDER_BASE_URL` | `https://carbon-intensity.example.invalid` | Public-safe placeholder base URL for the carbon intensity provider client. |
| `CARBON_API_CARBON_INTENSITY_PROVIDER_TIMEOUT_SECONDS` | `2.0` | Timeout, in seconds, for carbon intensity provider HTTP calls. |
| `CARBON_API_CARBON_INTENSITY_CACHE_TTL_SECONDS` | `900` | Redis cache TTL, in seconds, for successful carbon intensity provider responses. |

FastAPI docs and OpenAPI routes are disabled by default.

## Run locally without Docker

```sh
make run
```

Then check the liveness endpoint:

```sh
curl -i http://127.0.0.1:8000/healthz
```

Apply database migrations before calling workspace, usage ingestion, or reporting endpoints locally.

## Run locally with Docker

Optional: copy the safe local defaults before running Docker Compose.

```sh
cp example.env .env
```

Validate and build the local stack:

```sh
docker compose config
docker compose build
```

Start the API, PostgreSQL, and Redis:

```sh
docker compose up
```

In another terminal, test the API container through the host port:

```sh
curl -i http://localhost:8000/healthz
```

Expected response body:

```json
{"status":"ok"}
```

Stop and remove the local containers, networks, and volumes:

```sh
docker compose down --volumes --remove-orphans
```

## Database migrations

Start PostgreSQL, then apply the Alembic schema migration from the host before using workspace, usage ingestion, or reporting endpoints:

```sh
docker compose up --detach postgres
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

To roll back all local migrations:

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic downgrade base
```

The Docker Compose API container uses the same safe local placeholder credentials with the Compose service hostname `postgres`. It also sets `CARBON_API_REDIS_URL=redis://redis:6379/0` so Redis-backed cache code can use the Compose Redis service when called by future application flows.

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

Fetch one workspace, replacing the UUID with a value returned by the create or list call:

```sh
curl -i http://127.0.0.1:8000/workspaces/00000000-0000-0000-0000-000000000000
```

Duplicate workspace names return `409 Conflict`. Missing workspace IDs return `404 Not Found`.

## Usage sample ingestion API example

Ingest one usage sample for an existing workspace, replacing the UUID with a workspace ID returned by the workspace API:

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

Supported `resource_type` values are `vcpu`, `memory`, `storage`, and `network`. Supported `usage_unit` values are `vcpu_hour`, `vcpu_minute`, `gb_hour`, `gb_minute`, `gb_month`, `tb_month`, `gb`, `mb`, and `tb`; not every unit is compatible with every resource type. The endpoint returns the persisted sample with calculated `normalized_usage_amount`, `normalized_usage_unit`, `energy_kwh`, `carbon_intensity_grams_co2e_per_kwh`, `estimated_grams_co2e`, and `factor_source` fields. Missing workspaces return `404 Not Found`; incompatible resource/unit pairs return `422 Unprocessable Content`.

## Reporting API examples

Fetch a summary for one workspace, replacing the UUID with a workspace ID returned by the workspace API:

```sh
curl -i \
  'http://127.0.0.1:8000/workspaces/00000000-0000-0000-0000-000000000000/reports/summary?start_time=2026-01-01T00:00:00Z&end_time=2026-02-01T00:00:00Z'
```

Fetch a summary across all workspaces:

```sh
curl -i \
  'http://127.0.0.1:8000/reports/summary?start_time=2026-01-01T00:00:00Z&end_time=2026-02-01T00:00:00Z'
```

Report responses include the applied `time_range`, an overall `total`, and totals grouped in `by_workspace`, `by_provider`, and `by_region`. The `start_time` filter is inclusive and the `end_time` filter is exclusive; both must be timezone-aware when supplied. Invalid ranges where `start_time` is not before `end_time` return `422 Unprocessable Content`. Missing workspace-scoped reports return `404 Not Found`. Empty reports return zero totals with empty group arrays.

## Development commands

Repository tests require PostgreSQL. Start it first or use the full quality gate, which starts an isolated PostgreSQL service automatically.

```sh
docker compose up --detach postgres
make test
make lint
make typecheck
```

The full project gate is:

```sh
scripts/quality-gate.sh
```

When `docker-compose.yml` exists, the quality gate also validates the Compose file with `docker compose config`, starts an isolated PostgreSQL service for Alembic and repository tests, runs `alembic upgrade head`, and removes the test database volume during cleanup. Carbon intensity client tests use fakes and `httpx.MockTransport`; they do not call a live third-party API.

The quality gate also runs automation guardrails: shell syntax checks for project scripts, a public-safety term scan (`CARBON_API_PRIVATE_TERMS` may provide a comma-separated custom denylist), and a route-layering check that prevents route modules from importing persistence layers directly.

## Automation build loop

`scripts/build-loop.sh` runs bounded pi build cycles. It requires a clean working tree, pulls with `git pull --ff-only` when the branch has an upstream, refuses to start while ahead of upstream unless `--allow-ahead` or `PI_BUILD_ALLOW_AHEAD=1` is set, and stops if the upstream changes during a cycle.

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [ADR 0001: Project scope](docs/adr/0001-project-scope.md)
