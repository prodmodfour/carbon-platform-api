# carbon-platform-api

carbon-platform-api is an independent public portfolio project demonstrating backend and platform engineering with Python and FastAPI.

The long-term project goal is a production-style API for tracking compute-related carbon usage. The current T001 scope is intentionally small: a Python 3.12 FastAPI skeleton with one liveness endpoint.

## Public-safety constraints

This repository uses only public-safe sample code and documentation. Do not add employer code, private data, internal URLs, hostnames, credentials, screenshots, diagrams, or architecture. The project must not imply endorsement by any employer or organization.

## Current API

- `GET /healthz` returns `{"status": "ok"}`.

No database, Redis, Docker, carbon calculation logic, authentication, metrics, or external API clients are included yet.

## Requirements

- Python 3.12
- `uv` for dependency management and command execution
- `make`

## Setup

```sh
make install
```

## Run locally

```sh
make run
```

Then check the liveness endpoint:

```sh
curl http://127.0.0.1:8000/healthz
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

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [ADR 0001: Project scope](docs/adr/0001-project-scope.md)
