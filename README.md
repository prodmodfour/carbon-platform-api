# carbon-platform-api

carbon-platform-api is an independent public portfolio project demonstrating backend and platform engineering with Python and FastAPI.

The long-term project goal is a production-style API for tracking compute-related carbon usage. The current scope includes a Python 3.12 FastAPI skeleton, one liveness endpoint, and a Docker Compose local stack for the API, PostgreSQL, and Redis.

## Public-safety constraints

This repository uses only public-safe sample code and documentation. Do not add employer code, private data, internal URLs, hostnames, credentials, screenshots, diagrams, or architecture. The project must not imply endorsement by any employer or organization.

## Current API

- `GET /healthz` returns `{"status": "ok"}`.

PostgreSQL and Redis are available in the local Docker stack only. The application does not yet contain database models, migrations, Redis application code, carbon calculation logic, authentication, metrics, or external API clients.

## Requirements

- Python 3.12
- `uv` for dependency management and command execution
- `make`
- Docker with Docker Compose v2 for the local container stack

## Setup

```sh
make install
```

## Run locally without Docker

```sh
make run
```

Then check the liveness endpoint:

```sh
curl http://127.0.0.1:8000/healthz
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
curl http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

Stop and remove the local containers, networks, and volumes:

```sh
docker compose down --volumes --remove-orphans
```

## Development commands

```sh
make test
make lint
make typecheck
```

The full project gate is:

```sh
scripts/quality-gate.sh
```

When `docker-compose.yml` exists, the quality gate also validates the Compose file with `docker compose config`.

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [ADR 0001: Project scope](docs/adr/0001-project-scope.md)
