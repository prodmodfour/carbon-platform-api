# ADR 0002: Layered architecture and mockable boundaries

## Status

Accepted

## Context

After the initial FastAPI skeleton, the project needed workspace, usage ingestion, reporting, readiness, carbon calculation, cache, and external-provider code. Those features touch HTTP, validation, business rules, persistence, cache, and HTTP clients. Keeping those concerns mixed together would make the portfolio harder to test and easier to accidentally couple to private or non-public systems.

## Decision

Use the dependency direction documented in `AGENTS.md` and `docs/architecture.md`:

```text
routes -> schemas -> services -> repositories/clients -> database/cache/external APIs
```

Apply these boundaries:

- Route handlers handle HTTP concerns only.
- Pydantic schemas define public API and value-object shapes.
- Services own business validation and orchestration.
- Repositories own SQLAlchemy queries and persistence mapping.
- Clients own external HTTP calls.
- Cache modules own Redis serialization and commands.
- Services depend on small protocols where tests need fake implementations.

Add a route-layering check to the quality gate so route modules cannot import SQLAlchemy, Alembic, database/session helpers, models, or repositories directly.

## Consequences

- Business logic is testable without FastAPI request handling.
- Repository and client dependencies are mockable or replaceable in tests.
- Future providers can be added behind protocols without editing route handlers.
- Route handlers remain small and focused on HTTP translation.
- Some dependency wiring is more explicit, but the extra code keeps boundaries visible.
