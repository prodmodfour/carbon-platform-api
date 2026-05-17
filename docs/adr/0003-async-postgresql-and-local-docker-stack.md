# ADR 0003: Async PostgreSQL persistence and local Docker stack

## Status

Accepted

## Context

The project needed realistic persistence for workspaces, usage samples, and reporting while remaining safe for public portfolio use. It also needed repeatable local infrastructure for the API, PostgreSQL, Redis, and later observability tools. The implementation had to avoid real credentials and private infrastructure.

## Decision

Use PostgreSQL as the relational database, SQLAlchemy 2.x async APIs for application persistence, and Alembic for migrations. Keep all SQLAlchemy access inside repositories and database helper modules.

Use Docker Compose for local development with safe placeholder defaults:

- `api` for the FastAPI/Uvicorn container.
- `postgres` for PostgreSQL.
- `redis` for Redis.
- `prometheus` and `grafana` for local metrics exploration.

Keep Compose credentials local-only and documented as placeholders. Run the API container as a non-root user where practical. Validate Compose syntax in the local quality gate and CI.

## Consequences

- Repository integration tests can exercise real PostgreSQL behavior.
- Alembic provides explicit schema history and local rollback support.
- Async database access matches the FastAPI async request model.
- Docker Compose gives a repeatable local stack without requiring external services.
- The API does not auto-run migrations; operators and tests must run Alembic explicitly.
- Local placeholder credentials must not be reused for real deployments.
