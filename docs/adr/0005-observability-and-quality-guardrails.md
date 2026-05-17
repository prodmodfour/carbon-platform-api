# ADR 0005: Observability and quality guardrails

## Status

Accepted

## Context

The project aims to demonstrate production-style operational habits while remaining a local, public-safe portfolio service. It needs health checks, readiness checks, request correlation, metrics, local dashboards, and automated quality checks. It should not require hosted monitoring services, repository secrets, or deployment jobs.

## Decision

Provide three operational endpoints:

- `GET /healthz` for lightweight liveness with no dependency checks.
- `GET /readyz` for PostgreSQL and Redis readiness through service-level checks.
- `GET /metrics` for Prometheus text exposition.

Use structured JSON request logs with `X-Request-ID` propagation. Record HTTP request counters and latency histograms in an application-owned Prometheus registry.

Include local Prometheus and Grafana services in Docker Compose for metrics exploration only. Provision a local Prometheus datasource and a public-safe dashboard from repository files.

Use a local quality gate and GitHub Actions CI to run the same substantive checks: shell syntax checks, public-safety scanning, route-layering checks, Ruff, Ruff format, mypy, Docker Compose config validation, Alembic migration validation, and pytest with coverage.

## Consequences

- Liveness remains cheap and safe for container health checks.
- Readiness reports dependency state without leaking credentials or raw connection URLs.
- Metrics can be explored locally without hosted monitoring integrations.
- CI is useful for public pull requests and pushes without requiring secrets.
- The workflow validates quality but intentionally does not deploy or upload coverage.
- The public-safety scanner and layering checker are guardrails, not replacements for human review.
