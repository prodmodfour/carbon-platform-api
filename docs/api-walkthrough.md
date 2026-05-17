# Sample API walkthrough

This walkthrough uses only public-safe fake data. It assumes the local Docker stack is running and Alembic migrations have been applied.

## 1. Start local dependencies

```sh
cp example.env .env
docker compose up --detach
CARBON_API_DATABASE_URL=postgresql+asyncpg://carbon_platform_api:local_dev_password@localhost:5432/carbon_platform_api uv run alembic upgrade head
```

Set a local API base URL:

```sh
API_URL=http://127.0.0.1:8000
```

## 2. Check liveness and readiness

```sh
curl -i "$API_URL/healthz"
curl -i "$API_URL/readyz"
```

Expected liveness body:

```json
{"status":"ok"}
```

Expected healthy readiness body:

```json
{"status":"ready","dependencies":[{"name":"database","status":"ok"},{"name":"redis","status":"ok"}]}
```

## 3. Create a workspace

Use a timestamp suffix so repeated local walkthroughs do not collide with the unique workspace-name constraint.

```sh
WORKSPACE_NAME="Demo Workspace $(date +%s)"
WORKSPACE_ID=$(python3 - <<'PY' "$API_URL" "$WORKSPACE_NAME"
import json
import sys
import urllib.request

api_url = sys.argv[1]
workspace_name = sys.argv[2]
request = urllib.request.Request(
    f"{api_url}/workspaces",
    data=json.dumps({"name": workspace_name}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request) as response:
    payload = json.load(response)
print(payload["id"])
PY
)
echo "Created workspace: $WORKSPACE_ID"
```

List workspaces:

```sh
curl -i "$API_URL/workspaces"
```

Fetch the created workspace:

```sh
curl -i "$API_URL/workspaces/$WORKSPACE_ID"
```

## 4. Ingest a fake usage sample

This sample records 10 vCPU-hours in a fake region with a caller-supplied carbon intensity of 400 grams CO2e/kWh.

```sh
curl -i \
  -X POST "$API_URL/workspaces/$WORKSPACE_ID/usage-samples" \
  -H 'Content-Type: application/json' \
  -d '{
    "provider":"sample-cloud",
    "region":"sample-region-1",
    "resource_type":"vcpu",
    "usage_amount":"10",
    "usage_unit":"vcpu_hour",
    "measured_at":"2026-01-01T12:00:00Z",
    "carbon_intensity_grams_co2e_per_kwh":"400"
  }'
```

The response includes the raw usage fields plus deterministic demo calculation fields. For this sample, the default demo factor is `0.0500` kWh per vCPU-hour, so the calculated energy is `0.500000` kWh and the estimated emissions are `200.0000` grams CO2e.

These factors are public-safe demo values only. They are not authoritative measurements.

## 5. Read summary reports

Workspace-scoped summary:

```sh
curl -i \
  "$API_URL/workspaces/$WORKSPACE_ID/reports/summary?start_time=2026-01-01T00:00:00Z&end_time=2026-02-01T00:00:00Z"
```

All-workspaces summary:

```sh
curl -i \
  "$API_URL/reports/summary?start_time=2026-01-01T00:00:00Z&end_time=2026-02-01T00:00:00Z"
```

The report response includes:

```text
time_range      echoed inclusive start_time and exclusive end_time filters
total           usage sample count, total energy_kwh, total estimated_grams_co2e
by_workspace    totals grouped by workspace
by_provider     totals grouped by provider label
by_region       totals grouped by region label
```

## 6. Inspect metrics locally

Call metrics directly from the API:

```sh
curl -i "$API_URL/metrics"
```

Confirm Prometheus can see the API target after one scrape interval:

```sh
curl -i 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22carbon-platform-api%22%7D'
```

Open Grafana and view the provisioned local dashboard:

```sh
python3 -m webbrowser -t http://localhost:3000
```

Use the safe local placeholder login `local_admin` / `local_dev_password` unless you changed `.env`.

## 7. Clean up

```sh
docker compose down --volumes --remove-orphans
```

## Expected limitations during the walkthrough

- There is no authentication yet, so run the stack only in a trusted local development environment.
- The API does not auto-run migrations; apply Alembic before business endpoint calls.
- Usage ingestion uses caller-supplied carbon intensity values and does not call the carbon intensity provider or Redis cache.
- Prometheus and Grafana are local-only tools for metrics exploration.
