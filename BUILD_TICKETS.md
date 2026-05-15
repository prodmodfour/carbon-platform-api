# carbon-platform-api build tickets

AUTOMATION_STATUS: IN_PROGRESS

## Ticket status key

- TODO
- IN_PROGRESS
- DONE
- BLOCKED
- LOCKED

---

## T001 — Project skeleton

Status: DONE

Goal:
Create the initial Python/FastAPI project skeleton.

Requirements:
- Python 3.12 project using pyproject.toml.
- src/ layout under src/carbon_platform_api.
- Basic FastAPI app.
- GET /healthz returns {"status": "ok"}.
- pytest test for /healthz.
- ruff and mypy configuration.
- README.md.
- docs/architecture.md.
- docs/runbook.md.
- docs/adr/0001-project-scope.md.
- .gitignore.
- example.env.
- Makefile with install, test, lint, typecheck, and run commands.

Acceptance criteria:
- make test passes.
- make lint passes.
- make typecheck passes.
- README explains project purpose and public-safety constraints.
- No database, Redis, Docker, carbon logic, external API clients, or extra endpoints yet.



## T002 — Docker local environment

Status: DONE

Goal:
Add Docker support for local development without adding application database or Redis logic yet.

Requirements:
- Add Dockerfile for the FastAPI API.
- Add .dockerignore.
- Add docker-compose.yml with services:
  - api
  - postgres
  - redis
- API exposed on host port 8000.
- Postgres exposed on host port 5432.
- Redis exposed on host port 6379.
- Use environment variables in docker-compose.yml.
- Use safe local defaults only.
- Do not commit real secrets.
- API container must run as a non-root user where practical.
- Add container health check for the API using /healthz.
- Add Postgres and Redis health checks where practical.
- Update README with exact Docker commands.
- Update scripts/quality-gate.sh so it runs `docker compose config` when docker-compose.yml exists.

Scope limits:
- Do not add SQLAlchemy.
- Do not add Alembic.
- Do not add database models.
- Do not add Redis application code.
- Do not add carbon calculation logic.
- Do not add new API endpoints beyond /healthz.
- Do not unlock or implement T003.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- `docker compose config` passes.
- `docker compose build` passes.
- `docker compose up` starts api, postgres, and redis.
- `curl http://localhost:8000/healthz` returns `{"status":"ok"}`.
- README has exact local Docker run, test, and teardown commands.

---

## T003 — Config and structured logging

Status: TODO

Goal:
Add environment configuration and structured JSON logging without adding persistence, cache integration, carbon logic, or new business endpoints.

Requirements:
- Add `pydantic-settings` as a dependency if needed.
- Add a settings module using Pydantic settings.
- Settings should load from environment variables with a clear prefix, for example `CARBON_API_`.
- Include settings for:
  - app_name
  - app_version
  - environment
  - log_level
  - docs_enabled
- Keep docs/OpenAPI disabled by default.
- Add JSON structured logging using the standard library unless a dependency is strongly justified.
- Add request ID middleware.
- If the request includes `X-Request-ID`, propagate it.
- If no `X-Request-ID` is provided, generate one.
- Add `X-Request-ID` to every response.
- Request completion logs must include:
  - request_id
  - method
  - path
  - status_code
  - duration_ms
- Do not log secrets or full environment dumps.
- Add tests for settings defaults.
- Add tests for environment variable overrides.
- Add tests for request ID generation.
- Add tests for request ID propagation.
- Add tests that a completed request emits a structured log with the required fields.
- Update README if new environment variables are introduced.
- Update docs/architecture.md if middleware/config/logging structure is introduced.

Expected structure:
- `src/carbon_platform_api/config.py`
- `src/carbon_platform_api/logging.py`
- `src/carbon_platform_api/middleware/request_id.py`
- tests for config/logging/request ID behaviour

Scope limits:
- Do not add database models.
- Do not add SQLAlchemy.
- Do not add Alembic.
- Do not add Redis application logic.
- Do not add carbon calculation logic.
- Do not add workspace endpoints.
- Do not add `/readyz`.
- Do not add `/metrics`.
- Do not add authentication.
- Do not unlock or implement T004.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- App starts locally.
- App starts under Docker Compose.
- `GET /healthz` still returns `{"status":"ok"}`.
- `GET /healthz` response includes `X-Request-ID`.
- Supplied `X-Request-ID` is propagated.
- Logs are structured JSON.
- Request completion logs include request_id, method, path, status_code, and duration_ms.
- Tests cover config defaults, env overrides, request ID behaviour, and structured request logging.
## Future tickets

The following are intentionally LOCKED for Day 1. Do not implement them yet.

- T004 Database models and migrations
- T005 Workspace API
- T006 Carbon calculation service
- T007 Carbon intensity client with Redis cache
- T008 Usage sample ingestion
- T009 Reporting endpoints
- T010 Observability endpoints
- T011 Prometheus and Grafana local stack
- T012 GitHub Actions CI
- T013 Documentation polish
- T014 API key auth
- T015 Deployment docs / IaC
