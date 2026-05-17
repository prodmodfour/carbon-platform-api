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

Status: DONE

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

## T004 — Database models and migrations

Status: DONE

Goal:
Add PostgreSQL persistence with SQLAlchemy and Alembic migrations.

Requirements:
- Add SQLAlchemy 2.x.
- Add Alembic.
- Use async database access if feasible without excessive complexity.
- Add database configuration settings using the existing settings module.
- Add models:
  - workspaces
  - usage_samples
  - carbon_intensity_samples
- Add Alembic migration for the initial schema.
- Add repository layer for workspace CRUD only.
- Add integration tests for workspace repository behaviour.
- Tests should use a real PostgreSQL service where practical.
- Update README with migration commands.
- Update docs/architecture.md with the data model.
- Update scripts/quality-gate.sh only if needed to support database tests.

Expected structure:
- `src/carbon_platform_api/db/`
- `src/carbon_platform_api/models/`
- `src/carbon_platform_api/repositories/`
- `alembic/`
- `alembic.ini`

Scope limits:
- Do not add workspace API endpoints yet.
- Do not add carbon calculation logic.
- Do not add Redis application logic.
- Do not add carbon intensity external API client.
- Do not add reporting endpoints.
- Do not add `/readyz`.
- Do not add `/metrics`.
- Do not unlock or implement T005.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- `alembic upgrade head` works.
- Workspace repository can create, list, and fetch workspaces.
- Repository tests pass.
- No direct database logic appears in route handlers.

## TAUTO — Automation hardening

Status: DONE

Goal:
Prepare the project for multi-cycle autonomous implementation.

Requirements:
- Update `scripts/build-loop.sh` so the prompt requires the agent to select the lowest-numbered TODO or IN_PROGRESS ticket.
- Add remote sync checks before each cycle:
  - refuse to start if working tree is dirty
  - run `git pull --ff-only` when an upstream exists
  - refuse to continue if branch is ahead before a cycle starts unless explicitly allowed
  - refuse to continue if remote advanced during a cycle
- Add `scripts/check-no-private-terms.py` to fail if obvious private/employer/internal terms are committed.
- Add `scripts/check-layering.py` to fail if route modules import SQLAlchemy models, SQLAlchemy sessions, Alembic, or repositories directly in a way that bypasses services.
- Add both checks to `scripts/quality-gate.sh`.
- Expand `BUILD_TICKETS.md` so T005–T015 are full TODO ticket sections, not only locked bullet points.
- Add a final `T016 — Portfolio readiness audit` ticket.
- Do not implement application features in this ticket.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Build loop still works.
- Remaining backlog is explicit.
- Agent is instructed to use lowest-numbered ticket order.

## T005 — Workspace API

Status: DONE

Goal:
Expose workspace CRUD behaviour through HTTP while preserving service/repository boundaries.

Requirements:
- Add request and response schemas for workspaces.
- Add a workspace service that depends on a workspace repository abstraction.
- Add FastAPI dependencies for async database sessions and workspace service construction.
- Add workspace routes for:
  - `POST /workspaces`
  - `GET /workspaces`
  - `GET /workspaces/{workspace_id}`
- Validate duplicate workspace names with a clear client error.
- Return a clear 404 response for missing workspaces.
- Add endpoint tests using mockable service/repository boundaries where practical.
- Update README and docs/architecture.md with the new API surface.

Scope limits:
- Do not add carbon calculation logic.
- Do not add usage sample ingestion.
- Do not add Redis application logic.
- Do not add authentication.
- Do not add reporting, `/readyz`, or `/metrics` endpoints.
- Do not implement T006.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Workspace endpoints create, list, and fetch workspaces.
- Route handlers contain no direct SQLAlchemy or repository logic.
- Tests cover success, duplicate-name, and missing-workspace behaviour.
- Documentation lists the workspace endpoints and current limitations.

## T006 — Carbon calculation service

Status: DONE

Goal:
Add a deterministic carbon calculation service without adding new HTTP endpoints.

Requirements:
- Add schemas/value objects for calculation inputs and outputs.
- Add a service that calculates estimated grams CO2e from usage, resource type, region, and carbon intensity.
- Keep calculation factors public-safe and documented as sample/demo values.
- Make new calculation providers extensible through small protocols/interfaces.
- Add unit tests covering supported resource types, unit conversions, invalid inputs, and rounding.
- Update docs/architecture.md with the calculation flow and extension points.

Scope limits:
- Do not add ingestion or reporting endpoints.
- Do not add external carbon intensity API calls.
- Do not add Redis application logic.
- Do not add authentication.
- Do not implement T007.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Carbon calculation logic lives in services, not routes or repositories.
- Tests cover normal and edge cases with public-safe sample data.
- Documentation clearly states that factors are demo values, not authoritative measurements.

## T007 — Carbon intensity client with Redis cache

Status: DONE

Goal:
Add a mockable carbon intensity client and Redis-backed cache layer.

Requirements:
- Add settings for the carbon intensity provider base URL, timeout, and cache TTL.
- Add a small client protocol and implementation for fetching carbon intensity by region and time window.
- Add a Redis cache abstraction and implementation for carbon intensity samples.
- Add a fake client/cache for tests.
- Add service-level logic that reads cache first, calls the client on miss, and stores successful responses.
- Add tests for cache hit, cache miss, provider failure, timeout handling, and serialization.
- Update README, example.env, and docs/architecture.md with the new settings and flow.

Scope limits:
- Use only public documentation and safe sample URLs/defaults.
- Do not add usage ingestion or reporting endpoints.
- Do not add authentication.
- Do not implement T008.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- External calls are isolated in client modules and are mockable.
- Redis access is isolated behind a cache abstraction.
- Tests do not depend on a live third-party API.
- Documentation includes cache behaviour and failure limitations.

## T008 — Usage sample ingestion

Status: DONE

Goal:
Allow clients to ingest compute usage samples and persist calculated carbon estimates.

Requirements:
- Add usage ingestion request and response schemas.
- Add repository methods for storing usage samples.
- Add a usage ingestion service that validates workspace existence, calculates emissions, and persists usage samples.
- Add `POST /workspaces/{workspace_id}/usage-samples`.
- Add tests for successful ingestion, invalid workspace, invalid units, and persistence behaviour.
- Update README and docs/architecture.md with the ingestion endpoint and stored fields.

Scope limits:
- Do not add reporting endpoints.
- Do not add Prometheus/Grafana.
- Do not add authentication.
- Do not implement T009.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Usage sample ingestion persists data through repositories only.
- Route handlers do not perform calculations or direct database operations.
- Tests cover service and API behaviour.
- Documentation describes supported sample fields and limitations.

## T009 — Reporting endpoints

Status: DONE

Goal:
Expose basic carbon usage reports for workspaces.

Requirements:
- Add report schemas for totals grouped by workspace, provider, region, and time range.
- Add repository query methods dedicated to reporting reads.
- Add a reporting service that validates inputs and coordinates repository reads.
- Add endpoints for:
  - `GET /workspaces/{workspace_id}/reports/summary`
  - `GET /reports/summary`
- Support start/end time filters with clear validation errors.
- Add tests for empty reports, filtered reports, invalid ranges, and aggregation correctness.
- Update README and docs/architecture.md with report examples.

Scope limits:
- Do not add metrics/observability endpoints.
- Do not add authentication.
- Do not add dashboards.
- Do not implement T010.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Reporting queries live in repositories and business rules live in services.
- Endpoints return deterministic public-safe sample shapes.
- Tests cover aggregation and validation behaviour.
- Documentation describes report semantics and known limitations.

## T010 — Observability endpoints

Status: DONE

Goal:
Add production-style readiness and metrics endpoints.

Requirements:
- Add `GET /readyz` that checks database connectivity and Redis connectivity when Redis application code exists.
- Add `GET /metrics` with Prometheus-compatible process and HTTP request metrics.
- Preserve `GET /healthz` as a lightweight liveness endpoint.
- Add structured logs for readiness failures without leaking secrets.
- Add tests for healthy and unhealthy readiness cases.
- Add tests for metrics output shape.
- Update README and docs/runbook.md with operational checks.

Scope limits:
- Do not add Grafana dashboards or Compose observability services.
- Do not add tracing.
- Do not add authentication.
- Do not implement T011.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- `/readyz` reports dependency status without direct route-level database or Redis calls.
- `/metrics` returns Prometheus text format.
- Tests cover readiness and metrics behaviour.
- Operational documentation is updated.

## T011 — Prometheus and Grafana local stack

Status: DONE

Goal:
Add local observability infrastructure for metrics exploration.

Requirements:
- Extend Docker Compose with Prometheus and Grafana services.
- Add Prometheus scrape configuration for the API metrics endpoint.
- Add at least one Grafana dashboard JSON using public-safe sample panels.
- Use safe local default credentials only and document them as local placeholders.
- Add configuration validation tests where practical.
- Update README and docs/runbook.md with startup, login, and teardown commands.

Scope limits:
- Do not add external hosted monitoring integrations.
- Do not add tracing.
- Do not add authentication.
- Do not implement T012.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- `docker compose config` passes with the observability services.
- Prometheus can scrape the API locally.
- Grafana starts with the documented local dashboard.
- Documentation includes safe local commands and limitations.

## T012 — GitHub Actions CI

Status: TODO

Goal:
Add public-safe CI for linting, type checking, tests, and Docker validation.

Requirements:
- Add a GitHub Actions workflow for pull requests and pushes to the default branch.
- Run Ruff, Ruff format check, mypy, pytest, and Docker Compose config validation.
- Provide PostgreSQL for integration tests in CI.
- Cache dependencies where practical without adding secrets.
- Keep workflow names and logs public-safe.
- Update README with the CI checks.

Scope limits:
- Do not add deployment jobs.
- Do not add secret-dependent integrations.
- Do not add coverage upload services.
- Do not implement T013.

Acceptance criteria:
- `scripts/quality-gate.sh` passes locally.
- CI workflow syntax is valid.
- CI runs the same substantive checks as the local quality gate.
- No secrets or private URLs are required.
- Documentation mentions the CI contract.

## T013 — Documentation polish

Status: TODO

Goal:
Improve public portfolio documentation after the core API features exist.

Requirements:
- Refresh README with complete setup, API examples, and project scope.
- Refresh docs/architecture.md with final module boundaries and diagrams using text-only public-safe descriptions.
- Refresh docs/runbook.md with common operations and troubleshooting.
- Add or update ADRs for major design choices made since T001.
- Add a public-safe sample API walkthrough.
- Ensure docs do not imply employer endorsement or contain private details.

Scope limits:
- Do not add application features.
- Do not add deployment infrastructure.
- Do not add authentication changes.
- Do not implement T014.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Documentation is internally consistent and matches implemented behaviour.
- Public-safety constraints are visible to readers.
- API examples use only fake/sample data.
- Known limitations are clearly listed.

## T014 — API key auth

Status: TODO

Goal:
Add simple API key authentication suitable for a portfolio API demo.

Requirements:
- Add settings for enabling auth and configuring public-safe local API keys.
- Add an authentication dependency/service that validates API keys without logging secrets.
- Protect business endpoints while keeping `GET /healthz`, `GET /readyz`, and `GET /metrics` behaviour intentional and documented.
- Add tests for missing, invalid, and valid API keys.
- Update README, example.env, and docs/runbook.md with local auth usage.

Scope limits:
- Do not add OAuth, user accounts, or password storage.
- Do not add deployment secret managers.
- Do not implement T015.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Business endpoints require an API key when auth is enabled.
- Secrets are not logged or committed.
- Tests cover protected and unprotected endpoint behaviour.
- Documentation explains safe local configuration.

## T015 — Deployment docs / IaC

Status: TODO

Goal:
Document a public-safe deployment path and optional infrastructure-as-code skeleton.

Requirements:
- Add deployment documentation using generic cloud-neutral terminology or public provider examples only.
- Add an IaC skeleton only if it can be kept safe, minimal, and secret-free.
- Document required runtime settings, health checks, migrations, and rollback considerations.
- Add validation checks for any IaC files introduced.
- Update README with a deployment documentation link.

Scope limits:
- Do not add real cloud accounts, private hostnames, credentials, or employer-specific details.
- Do not add CI deployment jobs.
- Do not implement T016.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Deployment docs are public-safe and actionable at a high level.
- Any IaC included is minimal, validated, and uses placeholders only.
- Operational risks and rollback steps are documented.

## T016 — Portfolio readiness audit

Status: TODO

Goal:
Perform a final public-readiness and quality audit before considering the project complete.

Requirements:
- Review all tickets and mark the automation status complete only if all required work is done.
- Run the full quality gate and any relevant Docker smoke tests.
- Audit documentation, examples, logs, and configuration for public-safety issues.
- Audit architecture boundaries and tests for meaningful coverage.
- Fix only small polish issues found during the audit; create follow-up notes for anything larger.
- Update BUILD_NOTES.md with the final audit result.

Scope limits:
- Do not add new major features.
- Do not introduce private or employer-specific details.

Acceptance criteria:
- `scripts/quality-gate.sh` passes.
- Docker smoke tests pass where practical.
- Public-safety and architecture audits are documented.
- `AUTOMATION_STATUS` is set to `DONE` only if the full backlog is complete.
- Working tree is clean after the final commit.
