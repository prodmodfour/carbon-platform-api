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

## Docker teardown

```sh
docker compose down --volumes --remove-orphans
```

## Logging

Application request completion logs are JSON objects written through the standard library logging stack. Each completed request log includes `request_id`, `method`, `path`, `status_code`, and `duration_ms`.

Set `CARBON_API_LOG_LEVEL` to a standard library level such as `DEBUG`, `INFO`, or `WARNING` to adjust verbosity.

## Quality checks

Run individual checks:

```sh
make test
make lint
make typecheck
```

Run the full gate:

```sh
scripts/quality-gate.sh
```

The full gate validates Python checks and runs `docker compose config` when `docker-compose.yml` exists.

## Current operational limitations

- PostgreSQL and Redis are available only as local infrastructure; the application does not use them yet.
- No database migrations or persistent application storage.
- No Redis/cache application code.
- No authentication or authorization.
- No carbon usage ingestion or reporting endpoints.
- No metrics endpoint or tracing integration.
