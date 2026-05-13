# ADR 0001: Project scope

## Status

Accepted

## Context

carbon-platform-api is a public portfolio project intended to demonstrate backend and platform engineering practices without using employer code, private systems, private data, credentials, or non-public architecture.

The broader product direction is an API for tracking compute-related carbon usage. The first implementation step needs a safe, testable foundation before infrastructure, persistence, external integrations, or carbon domain logic are introduced.

## Decision

Start with a Python 3.12 FastAPI project skeleton that exposes only `GET /healthz` and includes development tooling, tests, and foundational documentation.

Do not include database, Redis, Docker, carbon calculations, external API clients, authentication, metrics, or additional endpoints in this initial scope.

## Consequences

- The initial API is easy to run and validate locally.
- Architecture boundaries are documented before more layers are added.
- Future tickets can add infrastructure and domain logic incrementally.
- The service is not functionally useful for carbon tracking until later tickets are completed.
