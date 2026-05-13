# Architecture

## Current scope

T001 provides only the initial FastAPI skeleton and a liveness endpoint. It intentionally does not include persistence, cache infrastructure, carbon calculations, authentication, metrics, Docker, or external API clients.

## Package layout

```text
src/carbon_platform_api/
  main.py              FastAPI app factory and ASGI app
  routes/health.py     HTTP route for GET /healthz
  schemas/health.py    Response schema for the health endpoint
```

## Dependency direction

The project follows this dependency direction as features are added:

```text
routes -> schemas -> services -> repositories/clients -> database/cache/external APIs
```

In T001, only `routes` and `schemas` exist because there is no business logic, persistence, cache, or external integration yet. Route handlers are limited to HTTP concerns and typed response construction.

## API surface

- `GET /healthz` returns a JSON liveness payload.

FastAPI documentation and OpenAPI routes are disabled for the skeleton so the only exposed endpoint is `/healthz`. API documentation endpoints can be introduced deliberately in a future ticket.
