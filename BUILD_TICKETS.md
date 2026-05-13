```md
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
Add Docker support for local development.

Requirements:
- Dockerfile.
- docker-compose.yml with api, postgres, redis.
- API exposed on port 8000.
- Environment variables loaded from .env or compose config.
- README updated with Docker commands.

Acceptance criteria:
- docker compose up starts the stack.
- /healthz works in the container.
- README has exact run commands.

---

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
