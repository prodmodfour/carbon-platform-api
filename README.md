# carbon-platform-api

carbon-platform-api is an independent public portfolio project demonstrating backend and platform engineering with Python and FastAPI.

The long-term project goal is a production-style API for tracking compute-related carbon usage. The current scope includes a Python 3.12 FastAPI skeleton, one liveness endpoint, environment-backed configuration, structured JSON request logging, request ID correlation, a Docker Compose local stack for the API, PostgreSQL, and Redis, and initial PostgreSQL models/migrations with a workspace repository.

## Public-safety constraints

This repository uses only public-safe sample code and documentation. Do not add employer code, private data, internal URLs, hostnames, credentials, screenshots, diagrams, or architecture. The project must not imply endorsement by any employer or organization.

## Current API

- `GET /healthz` returns `{"status": "ok"}` and includes an `X-Request-ID` response header.
- If a request supplies `X-Request-ID`, the same value is propagated to the response and request completion log. Otherwise, the API generates a request ID.

PostgreSQL persistence code currently consists of SQLAlchemy models, Alembic migrations, and a workspace repository. No workspace API endpoints are exposed yet. Redis remains available in the local Docker stack only; the application does not yet contain Redis application code, carbon calculation logic, authentication, metrics, or external API clients.

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

FastAPI docs and OpenAPI routes are disabled by default.

## Run locally without Docker

```sh
make run
```

Then check the liveness endpoint:

```sh
curl -i http://127.0.0.1:8000/healthz
```

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

Start PostgreSQL, then apply the Alembic schema migration from the host:

```sh
docker compose up --detach postgres
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

To roll back all local migrations:

```sh
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic downgrade base
```

The Docker Compose API container uses the same safe local placeholder credentials with the Compose service hostname `postgres`.

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

When `docker-compose.yml` exists, the quality gate also validates the Compose file with `docker compose config`, starts an isolated PostgreSQL service for Alembic and repository tests, runs `alembic upgrade head`, and removes the test database volume during cleanup.

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [ADR 0001: Project scope](docs/adr/0001-project-scope.md)
