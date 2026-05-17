# Runbook

## Local prerequisites

- Python 3.12
- `uv`
- `make`
- Docker with Docker Compose v2 for the local container stack

## Install dependencies

```sh
make install
```

## Start the API without Docker

```sh
make run
```

The API starts with Uvicorn on `http://127.0.0.1:8000` by default.

## Start the local Docker stack

Optional: copy the safe local Docker defaults before running Compose.

```sh
cp example.env .env
```

Validate and build the Compose stack:

```sh
docker compose config
docker compose build
```

Start the API, PostgreSQL, and Redis:

```sh
docker compose up
```

The API is exposed on `http://localhost:8000`, PostgreSQL on `localhost:5432`, and Redis on `localhost:6379`.

## Health check

```sh
curl -i http://127.0.0.1:8000/healthz
```

Expected response body:

```json
{"status":"ok"}
```

The response includes an `X-Request-ID` header. Supplying `X-Request-ID` on the request propagates the same value to the response and request completion log.

## Database migrations

Start PostgreSQL if it is not already running:

```sh
docker compose up --detach postgres
```

Apply the current Alembic schema before using workspace endpoints:

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

Roll back all local migrations:

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic downgrade base
```

## Workspace endpoint smoke checks

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

Fetch one workspace by replacing the UUID below with an ID returned by create or list:

```sh
curl -i http://127.0.0.1:8000/workspaces/00000000-0000-0000-0000-000000000000
```

Duplicate workspace names should return `409 Conflict`. Unknown workspace IDs should return `404 Not Found`.

## Docker teardown

```sh
docker compose down --volumes --remove-orphans
```

## Logging

Application request completion logs are JSON objects written through the standard library logging stack. Each completed request log includes `request_id`, `method`, `path`, `status_code`, and `duration_ms`.

Set `CARBON_API_LOG_LEVEL` to a standard library level such as `DEBUG`, `INFO`, or `WARNING` to adjust verbosity.

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

The full gate validates Python checks, runs `docker compose config`, starts an isolated PostgreSQL service, applies Alembic migrations, runs repository integration tests, and removes the quality-gate database volume during cleanup. It also runs public-safety and layering guardrails via `scripts/check-no-private-terms.py` and `scripts/check-layering.py`.

## Automation build loop

Use the build loop only from a clean working tree:

```sh
scripts/build-loop.sh --max-cycles 1
```

When an upstream branch exists, the loop runs `git pull --ff-only` before each cycle. It refuses to start while the branch is already ahead of upstream unless `--allow-ahead` or `PI_BUILD_ALLOW_AHEAD=1` is set, and it stops before push/continuation if the upstream advances during a cycle.

## Current operational limitations

- Workspace endpoints require the PostgreSQL schema to be migrated before use; the API does not auto-run migrations at startup.
- Redis is available only as local infrastructure; no Redis/cache application code exists yet.
- No authentication or authorization.
- No carbon usage ingestion or reporting endpoints.
- No metrics endpoint or tracing integration.
