# Runbook

## Local prerequisites

- Python 3.12
- `uv`
- `make`

## Install dependencies

```sh
make install
```

## Start the API

```sh
make run
```

The API starts with Uvicorn on `http://127.0.0.1:8000` by default.

## Health check

```sh
curl http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status": "ok"}
```

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

## Current operational limitations

- No database migrations or persistent storage.
- No Redis/cache dependency.
- No Docker Compose local stack.
- No authentication or authorization.
- No carbon usage ingestion or reporting endpoints.
- No metrics or structured logging beyond framework defaults.
