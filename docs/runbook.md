# Runbook

This runbook covers local operations for carbon-platform-api. All commands and examples use public-safe fake data and local placeholder credentials only.

## Local prerequisites

- Python 3.12
- `uv`
- `make`
- Docker with Docker Compose v2

## Install dependencies

```sh
make install
```

## Start the API without Docker

```sh
make run
```

The API starts with Uvicorn on `http://127.0.0.1:8000` by default. `GET /healthz` works without external dependencies. `GET /readyz` and business endpoints require configured PostgreSQL and Redis dependencies. Business endpoints also require an `X-API-Key` header when `CARBON_API_AUTH_ENABLED=true`.

## Start the full local Docker stack

Optional: copy the safe local Docker defaults before running Compose.

```sh
cp example.env .env
```

Validate and build the Compose stack:

```sh
docker compose config
docker compose build
```

Start the API, PostgreSQL, Redis, Prometheus, and Grafana:

```sh
docker compose up --detach
```

Local service ports:

| Service | URL or host port |
| --- | --- |
| API | `http://localhost:8000` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

## Apply database migrations

Workspace, usage ingestion, and reporting endpoints require the Alembic schema. The API does not auto-run migrations at startup.

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

Roll back all local migrations:

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic downgrade base
```

## Health check

```sh
curl -i http://127.0.0.1:8000/healthz
```

Expected response body:

```json
{"status":"ok"}
```

The response includes an `X-Request-ID` header. Supplying `X-Request-ID` on the request propagates the same value to the response and request completion log.

## Readiness check

Use readiness for dependency checks during local operations:

```sh
curl -i http://127.0.0.1:8000/readyz
```

A healthy API returns `200 OK` and reports PostgreSQL and Redis as `ok`:

```json
{"status":"ready","dependencies":[{"name":"database","status":"ok"},{"name":"redis","status":"ok"}]}
```

If PostgreSQL or Redis is unavailable, `/readyz` returns `503 Service Unavailable` and marks that dependency as `error`. Readiness failure logs include dependency names and exception types, not connection URLs or credentials.

## Metrics check

```sh
curl -i http://127.0.0.1:8000/metrics
```

The response uses Prometheus text exposition format and includes process metrics plus API HTTP request metrics such as `carbon_api_http_requests_total` and `carbon_api_http_request_duration_seconds`.

## Optional local API key auth

Authentication is disabled by default. To enable local API key checks for business endpoints, set `CARBON_API_AUTH_ENABLED=true` and configure one or more comma-separated placeholder keys:

```sh
CARBON_API_AUTH_ENABLED=true CARBON_API_AUTH_API_KEYS=local-demo-api-key make run
```

Then send the key on workspace, usage ingestion, and reporting requests:

```sh
curl -i -H 'X-API-Key: local-demo-api-key' http://127.0.0.1:8000/workspaces
```

Missing or invalid business endpoint keys return `401 Unauthorized` with a generic error. `GET /healthz`, `GET /readyz`, and `GET /metrics` intentionally remain unprotected so local health checks and Prometheus scraping do not need credentials.

Use only public-safe local placeholder keys in this repository. Do not commit real secrets or log API key values.

## Local Prometheus and Grafana checks

Prometheus scrapes `api:8000/metrics` from inside the Docker Compose network. Confirm that Prometheus is healthy:

```sh
curl -i http://localhost:9090/-/healthy
```

After one scrape interval, confirm that Prometheus can see the API target:

```sh
curl -i 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22carbon-platform-api%22%7D'
```

The query result should include a sample with value `1` for `job="carbon-platform-api"` when the API is reachable.

Grafana starts with a provisioned Prometheus datasource and the `Carbon Platform API Local Overview` dashboard. Open Grafana and sign in with the safe local placeholder values `local_admin` / `local_dev_password` unless overridden in `.env`:

```sh
python3 -m webbrowser -t http://localhost:3000
```

These Grafana values are local placeholders only. Do not reuse them for any real deployment.

## Workspace endpoint smoke checks

If local auth is enabled, add `-H 'X-API-Key: local-demo-api-key'` to each workspace, usage ingestion, and reporting curl command below.

Create a workspace after migrations are applied:

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

Fetch one workspace by replacing the UUID below with an ID returned by create/list:

```sh
curl -i http://127.0.0.1:8000/workspaces/00000000-0000-0000-0000-000000000000
```

Expected errors:

- Duplicate workspace name: `409 Conflict`.
- Unknown workspace ID: `404 Not Found`.

## Usage ingestion smoke check

After creating a workspace, ingest one public-safe sample by replacing the UUID with the created workspace ID:

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

The response should include persisted raw fields plus calculated `normalized_usage_amount`, `normalized_usage_unit`, `energy_kwh`, `estimated_grams_co2e`, and `factor_source`.

Expected errors:

- Unknown workspace ID: `404 Not Found`.
- Incompatible resource/unit pair: `422 Unprocessable Content`.
- Missing timezone on `measured_at`: `422 Unprocessable Content`.

## Reporting smoke checks

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

Expected response shape includes `time_range`, `total`, `by_workspace`, `by_provider`, and `by_region`. Empty reports return zero totals and empty groups.

Expected errors:

- `start_time` at or after `end_time`: `422 Unprocessable Content`.
- Naive timestamps without timezone offsets: `422 Unprocessable Content`.
- Unknown workspace ID for workspace-scoped reports: `404 Not Found`.

## Logging

Application request completion logs are JSON objects written through the standard library logging stack. Each completed request log includes `request_id`, `method`, `path`, `status_code`, and `duration_ms`.

Set `CARBON_API_LOG_LEVEL` to a standard library level such as `DEBUG`, `INFO`, or `WARNING` to adjust verbosity. Do not log credentials, raw environment dumps, or private data.

## Quality checks

Run individual checks. Repository tests require PostgreSQL, so start it before `make test` when not using the full gate.

```sh
docker compose up --detach postgres
make test
make lint
make typecheck
```

Run the full gate:

```sh
scripts/quality-gate.sh
```

The full gate validates shell syntax, public-safety scanning, route-layering rules, Ruff, Ruff format, mypy, Docker Compose syntax, Alembic migrations, and pytest coverage. It starts an isolated PostgreSQL service and removes the quality-gate database volume during cleanup.

## Common operations

### Reset the local database

This removes local PostgreSQL data and recreates it from migrations:

```sh
docker compose down --volumes --remove-orphans
docker compose up --detach postgres
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

### Validate Docker configuration only

```sh
docker compose config
```

### View API container logs

```sh
docker compose logs --follow api
```

### Stop all local services

```sh
docker compose down --volumes --remove-orphans
```

## Troubleshooting

| Symptom | Likely cause | Suggested check |
| --- | --- | --- |
| `/healthz` fails in Docker | API container is not running or still starting | `docker compose ps` and `docker compose logs api` |
| `/readyz` returns `503` with database error | PostgreSQL is unavailable or `CARBON_API_DATABASE_URL` is wrong | `docker compose ps postgres` and verify the URL uses the right host (`localhost` on host, `postgres` inside Compose) |
| `/readyz` returns `503` with Redis error | Redis is unavailable or `CARBON_API_REDIS_URL` is wrong | `docker compose ps redis` and verify the URL uses the right host (`localhost` on host, `redis` inside Compose) |
| Workspace endpoint returns a database table error | Alembic migrations were not applied | Run `uv run alembic upgrade head` with the correct database URL |
| Usage ingestion returns `422` | Invalid request shape, missing timezone, non-positive usage, or incompatible resource/unit pair | Compare the request body with the smoke-check example |
| Report endpoint returns `422` | Time filters are naive or `start_time` is not before `end_time` | Use timezone-aware ISO timestamps such as `2026-01-01T00:00:00Z` |
| Prometheus target is down | API is not reachable inside the Compose network | Check `docker compose ps api prometheus` and Prometheus target query |
| Grafana has no dashboard data | Prometheus has not scraped yet or the API has no traffic | Wait one scrape interval, call API endpoints, then refresh Grafana |
| Quality gate cannot start PostgreSQL | Docker is not running or the test port is already used | Start Docker or set `CARBON_API_TEST_POSTGRES_HOST_PORT` to another local port |

## Automation build loop

Use the build loop only from a clean working tree:

```sh
scripts/build-loop.sh --max-cycles 1
```

When an upstream branch exists, the loop runs `git pull --ff-only` before each cycle. It refuses to start while the branch is already ahead of upstream unless `--allow-ahead` or `PI_BUILD_ALLOW_AHEAD=1` is set, and it stops before continuation if the upstream advances during a cycle.

## Current operational limitations

- Workspace, usage ingestion, and reporting endpoints require explicit Alembic migrations.
- Carbon calculation factors and conversions are public-safe demo values only, not authoritative measurements.
- Usage ingestion uses caller-supplied carbon intensity values and does not call the carbon intensity provider or Redis cache.
- Direct carbon intensity lookup is not exposed through HTTP.
- API key auth is a simple local demo mechanism only; it does not provide OAuth, user accounts, password storage, key rotation, rate limiting, or authorization roles.
- Prometheus and Grafana are local-only Compose services for metrics exploration.
- Grafana uses safe local placeholder credentials by default and is not production-hardened.
- No tracing integration, hosted monitoring integration, deployment automation, or secret-management integration is configured.
