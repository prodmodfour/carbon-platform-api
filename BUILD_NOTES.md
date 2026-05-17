# Build notes

AUTOMATION_STATUS: IN_PROGRESS

## Current summary

T007 is complete. The project now includes a mockable carbon intensity provider client, carbon intensity query/sample schemas, a Redis-backed cache abstraction/implementation, and a cache-first carbon intensity service. Provider HTTP calls are isolated in `clients/`, Redis access is isolated in `cache/`, and tests use fakes plus `httpx.MockTransport` instead of a live third-party API.

## Last completed ticket

T007 — Carbon intensity client with Redis cache.

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

2026-05-15:
- T003: `uv run ruff check .` — passed.
- T003: `uv run ruff format --check .` — passed.
- T003: `uv run mypy src tests` — passed.
- T003: `uv run pytest --cov=src --cov-report=term-missing` — passed with 10 tests and 96% total coverage.
- T003: local Uvicorn startup check — passed; `GET /healthz` returned `{"status":"ok"}`.
- T003: `sudo -n docker compose build` — passed.
- T003: `sudo -n docker compose up --detach` — passed; `GET /healthz` returned `{"status":"ok"}` with `X-Request-ID` from the API container.
- T003: `sudo -n docker compose down --volumes --remove-orphans` — passed via cleanup trap.
- T003: `scripts/quality-gate.sh` — passed with Ruff, Ruff format check, mypy, pytest coverage, and `docker compose config`.

2026-05-17:
- T004: `uv run ruff check .` — passed.
- T004: `uv run ruff format --check .` — passed.
- T004: `uv run mypy src tests` — passed.
- T004: `scripts/quality-gate.sh` — passed with Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, `alembic upgrade head`, and pytest coverage. Pytest passed with 12 tests and 97% total coverage.
- TAUTO: `uv run ruff check .` — passed.
- TAUTO: `uv run ruff format --check .` — passed after formatting the new automation scripts.
- TAUTO: `uv run mypy src tests` — passed.
- TAUTO: `uv run python scripts/check-no-private-terms.py` — passed.
- TAUTO: `uv run python scripts/check-layering.py` — passed.
- TAUTO: `uv run pytest tests/test_automation_checks.py -q` — passed with 8 tests.
- TAUTO: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, `alembic upgrade head`, and pytest coverage. Pytest passed with 20 tests and 97% total coverage.
- T005: `uv run ruff check .` — passed.
- T005: `uv run ruff format --check .` — passed.
- T005: `uv run mypy src tests` — passed.
- T005: `uv run pytest tests/test_workspace_api.py -q` — passed with 3 endpoint tests.
- T005: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, `alembic upgrade head`, and pytest coverage. Pytest passed with 23 tests and 95% total coverage.
- T006: `uv run pytest tests/test_carbon_calculations.py -q` — passed with 16 unit tests.
- T006: `uv run ruff check .` — passed.
- T006: `uv run ruff format --check .` — passed.
- T006: `uv run mypy src tests` — passed.
- T006: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, `alembic upgrade head`, and pytest coverage. Pytest passed with 39 tests and 95% total coverage.
- T007: `uv run pytest tests/test_config.py tests/test_carbon_intensity.py -q` — passed with 11 tests.
- T007: `uv run ruff check .` — passed.
- T007: `uv run ruff format --check .` — passed.
- T007: `uv run mypy src tests` — passed.
- T007: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, `alembic upgrade head`, and pytest coverage. Pytest passed with 48 tests and 92% total coverage.

## Limitations

- Workspace endpoints require the PostgreSQL schema to be migrated before use; the API does not auto-run Alembic migrations at startup.
- Carbon calculation factors and conversions are public-safe demo values only, not authoritative energy or emissions measurements.
- Carbon calculation and carbon intensity lookup services are not exposed through HTTP endpoints yet.
- The default carbon intensity provider URL is a public-safe `.invalid` placeholder; tests use fakes and do not depend on a live provider.
- Redis cache code exists, but no current API endpoint calls it until usage ingestion/reporting flows are added.
- FastAPI docs/OpenAPI routes remain disabled by default; they are exposed only when `CARBON_API_DOCS_ENABLED=true`.
- Automation guardrails now exist, but they are intentionally conservative checks and do not replace human review for public-safety or architecture issues.
- No usage sample ingestion, authentication, metrics endpoint, or reporting endpoints are included.

## Notes for next cycle

Recommended next ticket: T008 — Usage sample ingestion.
