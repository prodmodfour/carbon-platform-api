# Build notes

AUTOMATION_STATUS: IN_PROGRESS

## Current summary

TAUTO is complete. The project now has hardened autonomous build-loop guardrails, explicit lowest-numbered ticket selection instructions, public-safety and route-layering checks in the quality gate, tests for those automation checks, and explicit TODO ticket sections for T005 through T016. No application features or new API endpoints were added.

## Last completed ticket

TAUTO — Automation hardening.

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

## Limitations

- Only `GET /healthz` is implemented as a business/API endpoint.
- FastAPI docs/OpenAPI routes remain disabled by default; they are exposed only when `CARBON_API_DOCS_ENABLED=true`.
- PostgreSQL persistence currently exists only as models, migrations, async database helpers, and the workspace repository; no API route uses it yet.
- Redis is available as local Docker infrastructure only; the application does not connect to it yet.
- Automation guardrails now exist, but they are intentionally conservative checks and do not replace human review for public-safety or architecture issues.
- No carbon calculations, external API clients, authentication, metrics endpoint, reporting endpoints, or additional business endpoints are included.

## Notes for next cycle

Recommended next ticket: T005 — Workspace API.
