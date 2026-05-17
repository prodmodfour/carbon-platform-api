# Deployment guide

This guide describes a public-safe, cloud-neutral deployment path for carbon-platform-api. It uses generic platform terms and placeholder values only. Do not copy local demo credentials, real account details, private data, private hostnames, screenshots, or organization-specific architecture into this repository.

No infrastructure-as-code skeleton is included in this repository. A useful IaC template would need a target platform choice, and adding one without that context would either overbuild the portfolio project or risk embedding provider-specific assumptions. If IaC is added later, keep it minimal, secret-free, placeholder-only, and validate it with the platform's format and validation commands before committing it.

## Reference deployment shape

A production-style deployment can be assembled from these generic components:

```text
API callers
  -> HTTPS load balancer or ingress
      -> carbon-platform-api container on port 8000
          -> PostgreSQL database
          -> Redis cache
          -> optional carbon intensity provider endpoint
Metrics scraper
  -> GET /metrics on the API container or service
Log collector
  <- structured JSON logs from the API process
```

Recommended platform capabilities:

- A container runtime that can run the image built from this repository's `Dockerfile`.
- A managed or self-operated PostgreSQL database compatible with the async SQLAlchemy URL.
- A managed or self-operated Redis instance compatible with `redis://` or `rediss://` URLs.
- A secret store or environment injection mechanism for runtime settings.
- HTTPS termination before traffic reaches the API container.
- A metrics scraper that understands Prometheus text exposition.

Keep the API container stateless. PostgreSQL is the durable system of record; Redis stores cache entries and is not the source of truth.

## Runtime settings checklist

Set runtime configuration with `CARBON_API_*` environment variables. Do not commit real values to source control, container images, screenshots, or tickets.

| Setting | Required for deployment | Guidance |
| --- | --- | --- |
| `CARBON_API_APP_NAME` | Optional | Keep the default unless the platform needs a different display name. |
| `CARBON_API_APP_VERSION` | Recommended | Set to the deployed image or release version for log correlation. |
| `CARBON_API_ENVIRONMENT` | Recommended | Use a generic label such as `staging` or `production`. |
| `CARBON_API_LOG_LEVEL` | Recommended | Use `INFO` for normal operation; avoid verbose logs in shared environments. |
| `CARBON_API_DOCS_ENABLED` | Recommended | Keep `false` unless interactive docs are intentionally exposed in a controlled environment. |
| `CARBON_API_AUTH_ENABLED` | Recommended | Use `true` for any shared deployment because business endpoints are otherwise open. |
| `CARBON_API_AUTH_API_KEYS` | Required when auth is enabled | Supply opaque keys from a secret store. Rotate outside this repository. |
| `CARBON_API_DATABASE_URL` | Required | Supply a PostgreSQL URL for the target database. Treat it as a secret. |
| `CARBON_API_REDIS_URL` | Required for readiness/cache | Supply a Redis URL for the target cache. Treat credential-bearing URLs as secrets. |
| `CARBON_API_CARBON_INTENSITY_PROVIDER_BASE_URL` | Optional | Leave as a placeholder unless a public provider has been selected and tested. |
| `CARBON_API_CARBON_INTENSITY_PROVIDER_TIMEOUT_SECONDS` | Optional | Keep a small timeout so provider issues do not tie up workers. |
| `CARBON_API_CARBON_INTENSITY_CACHE_TTL_SECONDS` | Optional | Tune to match provider freshness needs if the intensity service is used. |

The local defaults in `example.env` are placeholders for Docker Compose demos only. Replace them for any shared environment.

## Image build and release artifact

Build a tagged container image from a clean, tested commit:

```sh
docker build -t registry.example.invalid/carbon-platform-api:0.1.0 .
```

Push the image to the selected registry using the platform's normal authenticated workflow:

```sh
docker push registry.example.invalid/carbon-platform-api:0.1.0
```

The registry hostname and tag above are placeholders. Use immutable release tags or digests for repeatable rollbacks. Do not bake runtime secrets into the image; inject them at runtime.

## Database migrations

The API does not auto-run Alembic migrations at startup. Run migrations as an explicit release step after backing up the target database and before sending production traffic to a new application version.

Example migration command with placeholder values:

```sh
CARBON_API_DATABASE_URL='postgresql+asyncpg://<user>:<password>@<host>:5432/<database>' \
  uv run alembic upgrade head
```

Recommended migration practice:

1. Confirm the target database is reachable from the migration runner.
2. Confirm the migration runner has schema-change permissions.
3. Run `uv run alembic upgrade head` exactly once per release environment.
4. Save the command output with the release notes.
5. Start or roll forward API containers only after migrations succeed.

Avoid destructive schema changes unless a tested rollback and data recovery plan exists.

## Startup and health checks

Run the container command from the `Dockerfile` or an equivalent ASGI server command:

```text
uvicorn carbon_platform_api.main:app --host 0.0.0.0 --port 8000
```

Expose container port `8000` behind the platform's HTTPS load balancer or ingress. Configure health probes with the existing operational endpoints:

| Probe | Endpoint | Expected use |
| --- | --- | --- |
| Liveness | `GET /healthz` | Confirms the API process can answer lightweight requests without dependency checks. |
| Readiness | `GET /readyz` | Confirms PostgreSQL and Redis connectivity before the instance receives traffic. |
| Metrics | `GET /metrics` | Provides Prometheus-compatible process and HTTP request metrics. |

Suggested starting probe values:

- Liveness initial delay: 10 seconds.
- Liveness period: 30 seconds.
- Readiness period: 10 seconds.
- Probe timeout: 5 seconds.

`GET /healthz`, `GET /readyz`, and `GET /metrics` intentionally remain unprotected by API key auth. Place them behind platform network controls if the deployment is reachable beyond a trusted operations boundary.

## Rollout checklist

Use a boring release sequence:

1. Run `scripts/quality-gate.sh` on the release commit.
2. Build and push an immutable image tag or digest.
3. Provision PostgreSQL and Redis with backups enabled where the platform supports it.
4. Configure runtime settings through the platform's environment and secret mechanisms.
5. Run `uv run alembic upgrade head` against the target database.
6. Deploy the API container image.
7. Check `GET /healthz`, `GET /readyz`, and `GET /metrics`.
8. Send a small authenticated smoke request to a business endpoint if auth is enabled.
9. Watch structured JSON logs, request error rates, readiness status, and latency during the rollout window.

## Rollback plan

Prefer rollback steps that keep data safe:

1. Stop sending new traffic to the failing release.
2. Redeploy the previous known-good image tag or digest.
3. Confirm `GET /healthz` and `GET /readyz` are healthy on the rolled-back version.
4. Review logs for migration or compatibility errors before scaling traffic back up.

Database rollback needs extra care. Alembic downgrades can remove schema or data, so do not run them automatically. If a schema rollback is required, restore from backup or run a tested targeted downgrade after confirming the exact revision and data impact:

```sh
CARBON_API_DATABASE_URL='postgresql+asyncpg://<user>:<password>@<host>:5432/<database>' \
  uv run alembic downgrade <target-revision>
```

Design future migrations to be backward compatible when possible: deploy additive schema changes first, roll application code second, and remove old columns only after all old application versions are gone.

## Operational risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Migrations are skipped | Keep migrations as a required release step and fail deployment if `uv run alembic upgrade head` fails. |
| Runtime secrets leak | Store API keys and connection URLs outside source control and avoid logging raw environment values. |
| Operational endpoints are exposed | Restrict access with platform networking controls while keeping probes and metrics functional. |
| Database and application versions drift | Tag images immutably and record the Alembic revision applied for each release. |
| Redis is unavailable | `/readyz` reports Redis as unhealthy; cached carbon intensity lookups should be treated as unavailable until Redis recovers. |
| Carbon intensity provider is unavailable | Keep provider timeouts small and rely on mockable service boundaries; current business endpoints do not call the provider. |
| Demo carbon factors are misunderstood | Document that estimates are deterministic demo values, not authoritative measurements. |
| Observability is incomplete | Add platform-native logs, metrics scraping, and alerts; this repository only includes local Prometheus/Grafana examples. |

## What this guide does not include

- No real cloud accounts, hostnames, credentials, or organization-specific deployment details.
- No CI deployment jobs.
- No secret-management integration code.
- No Terraform, Kubernetes, or other IaC files.
- No production hardening for Grafana or hosted monitoring.

These omissions are intentional for a public portfolio project. Add platform-specific deployment automation only in a separate, bounded ticket with secret-free placeholders and validation checks.
