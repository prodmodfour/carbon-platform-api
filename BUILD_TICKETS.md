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

Status: TODO

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
- README has exact local Docker run, test, and teardown commands.---

## Future tickets

The following are intentionally LOCKED for Day 1. Do not implement them yet.

- T003 Config and structured logging
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
