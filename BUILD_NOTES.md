# Build notes

AUTOMATION_STATUS: IN_PROGRESS

## Current summary

T002 is complete. The repository now has Docker support for local development: an API Dockerfile, Docker Compose services for `api`, `postgres`, and `redis`, safe local environment defaults, container health checks, README/runbook/architecture documentation, and tests covering the Docker configuration.

## Last completed ticket

T002 — Docker local environment.

## Current blockers

None.

## Quality gate history

2026-05-13:
- T001: `make test` — passed.
- T001: `make lint` — passed after formatting `src/carbon_platform_api/main.py` with Ruff.
- T001: `make typecheck` — passed.
- T001: `scripts/quality-gate.sh` — passed with Ruff, mypy, pytest, and coverage.
- T002: `uv run ruff check .` — passed.
- T002: `uv run ruff format --check .` — passed.
- T002: `uv run mypy src tests` — passed.
- T002: `uv run pytest --cov=src --cov-report=term-missing` — passed with 4 tests and 100% coverage.
- T002: `docker compose config` — passed.
- T002: `sudo -n docker compose build` — passed. `sudo` was needed in this environment because the current user does not have direct Docker socket access.
- T002: `sudo -n docker compose up --detach` — passed; `api`, `postgres`, and `redis` reached healthy/running states.
- T002: `curl --fail --silent http://localhost:8000/healthz` — returned `{"status":"ok"}`.
- T002: `sudo -n docker compose down --volumes --remove-orphans` — passed.
- T002: `scripts/quality-gate.sh` — passed with Ruff, Ruff format check, mypy, pytest coverage, and `docker compose config`.

## Limitations

- Only `GET /healthz` is implemented.
- FastAPI docs/OpenAPI routes remain disabled so no extra endpoints are exposed.
- PostgreSQL and Redis are available as local Docker infrastructure only; the application does not connect to them yet.
- No SQLAlchemy, Alembic, database models, Redis application code, carbon calculations, external API clients, authentication, metrics, or additional API endpoints are included.

## Notes for next cycle

Recommended next ticket: T003 Config and structured logging, when future tickets are unlocked.
