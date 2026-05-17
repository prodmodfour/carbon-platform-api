# Build notes

AUTOMATION_STATUS: IN_PROGRESS

## Current summary

T011 is complete. The local Docker Compose stack now includes Prometheus and Grafana for metrics exploration. Prometheus scrapes the API's `/metrics` endpoint over the Compose network, and Grafana provisions a local Prometheus datasource plus a public-safe `Carbon Platform API Local Overview` dashboard. Documentation now includes startup, validation, login, and teardown commands with safe local placeholder credentials.

## Last completed ticket

T011 — Prometheus and Grafana local stack.

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
- T008: `uv run ruff format .` — formatted the new usage sample schema/API test files before final checks.
- T008: `uv run ruff check .` — passed.
- T008: `uv run ruff format --check .` — passed.
- T008: `uv run mypy src tests` — passed.
- T008: `uv run pytest tests/test_usage_ingestion_service.py tests/test_usage_samples_api.py tests/test_models.py -q` — passed with 8 tests.
- T008: `uv run python scripts/check-layering.py` — passed.
- T008: `uv run python scripts/check-no-private-terms.py` — passed.
- T008: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, Alembic upgrades through `20260517_0002`, and pytest coverage. Pytest passed with 56 tests and 93% total coverage.
- T009: `uv run ruff check .` — passed.
- T009: `uv run ruff format --check .` — passed.
- T009: `uv run mypy src tests` — passed.
- T009: `uv run pytest tests/test_reporting_service.py tests/test_reports_api.py -q` — passed with 8 tests.
- T009: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, Alembic upgrades through `20260517_0002`, and pytest coverage. Pytest passed with 66 tests and 94% total coverage.
- T010: `uv run ruff check .` — passed.
- T010: `uv run ruff format --check .` — passed.
- T010: `uv run mypy src tests` — passed.
- T010: `uv run pytest tests/test_readiness_service.py tests/test_observability_api.py -q` — passed with 7 tests.
- T010: `uv run python scripts/check-layering.py` — passed.
- T010: `uv run python scripts/check-no-private-terms.py` — passed.
- T010: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, Alembic upgrades through `20260517_0002`, and pytest coverage. Pytest passed with 73 tests and 95% total coverage.
- T011: `docker compose config` — passed with Prometheus and Grafana services.
- T011: `uv run pytest tests/test_observability_stack_configuration.py tests/test_docker_configuration.py -q` — passed with 7 configuration tests.
- T011: `uv run ruff check .` — passed.
- T011: `uv run mypy src tests` — passed.
- T011: `uv run ruff format --check .` — passed.
- T011: `uv run python scripts/check-no-private-terms.py` — passed.
- T011: `scripts/quality-gate.sh` — passed with shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format check, mypy, `docker compose config`, isolated PostgreSQL startup, Alembic upgrades through `20260517_0002`, and pytest coverage. Pytest passed with 77 tests and 95% total coverage.
- T011: Docker observability smoke test — passed using an isolated Compose project and alternate host ports; API, Prometheus, and Grafana health checks passed, Prometheus returned `up{job="carbon-platform-api"}=1`, Grafana returned the provisioned dashboard from its API, and the stack was torn down with volumes removed.

## Limitations

- Workspace, usage ingestion, and reporting endpoints require the PostgreSQL schema to be migrated before use; the API does not auto-run Alembic migrations at startup.
- Carbon calculation factors and conversions are public-safe demo values only, not authoritative energy or emissions measurements.
- Usage ingestion requires caller-supplied carbon intensity values; it does not call the carbon intensity provider or Redis cache.
- Direct carbon intensity lookup is not exposed through HTTP yet.
- The default carbon intensity provider URL is a public-safe `.invalid` placeholder; tests use fakes and do not depend on a live provider.
- Redis cache code exists, but no current business endpoint calls it yet; readiness pings Redis only for dependency status.
- Reporting uses simple aggregate queries over persisted usage samples only; it does not provide time buckets, rollups, pagination, or materialized summaries.
- FastAPI docs/OpenAPI routes remain disabled by default; they are exposed only when `CARBON_API_DOCS_ENABLED=true`.
- Automation guardrails now exist, but they are intentionally conservative checks and do not replace human review for public-safety or architecture issues.
- Prometheus and Grafana are included only as local Docker Compose services for metrics exploration; no hosted monitoring integration, alerting, or tracing is configured.
- Grafana uses safe local placeholder credentials by default and is not production-hardened.
- Authentication is not included yet.

## Notes for next cycle

Recommended next ticket: T012 — GitHub Actions CI.
