# Agent instructions for carbon-platform-api

## Project purpose

carbon-platform-api is an independent public portfolio project demonstrating backend and platform engineering.

It is a production-style API for tracking compute-related carbon usage using FastAPI, PostgreSQL, Redis, Docker Compose, tests, CI/CD, Prometheus metrics, Grafana dashboards, structured logging, health/readiness checks, and documentation.

## Public-safety constraints

Do not use employer code, private data, internal URLs, hostnames, credentials, screenshots, diagrams, or architecture.

Use only public-safe fake/sample data.

This project must not imply endorsement by any employer.

## Engineering style

Prefer boring, clear, maintainable code over clever code.

Every feature must have meaningful tests.

Every external dependency must be mockable.

Do not overbuild beyond the current ticket.

Do not silently skip acceptance criteria.

## Architecture rules

Apply SOLID principles as concrete constraints:

- Single Responsibility: route handlers handle HTTP only; business logic belongs in services; persistence belongs in repositories; external APIs belong in clients.
- Open/Closed: new providers should be added via interfaces/protocols, not by editing core calculation logic.
- Liskov Substitution: fake clients must be substitutable for real clients in tests.
- Interface Segregation: keep repository/client/service interfaces small and specific.
- Dependency Inversion: services depend on abstractions/protocols, not concrete implementations.

Required dependency direction:

routes -> schemas -> services -> repositories/clients -> database/cache/external APIs

Forbidden:

- Business logic in FastAPI route handlers.
- Direct SQLAlchemy queries inside route handlers.
- Direct HTTP calls inside route handlers.
- Mixing API, persistence, calculation, and external integration in one module.
- Committing secrets.
- Adding real employer-specific details.

## Quality gates

Before committing, run the relevant checks. Prefer the full project gate when possible:

```sh
scripts/quality-gate.sh
```

If a check fails, fix it before committing.

Automation behaviour

When invoked by scripts/build-loop.sh:

1. Read AGENTS.md, BUILD_TICKETS.md, and BUILD_NOTES.md.
2. Select the next incomplete ticket.
3. Implement exactly one bounded ticket.
4. Add or update tests.
5. Run quality gates.
6. Update BUILD_NOTES.md.
7. Mark the ticket complete only if acceptance criteria are met.
8. Commit the completed ticket.
8. Leave the working tree clean.

Do not attempt multiple tickets in one cycle.
