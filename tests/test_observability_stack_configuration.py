"""Tests for local Prometheus and Grafana configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = "observability/grafana/dashboards/carbon-platform-api-overview.json"


def read_project_file(relative_path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_dashboard() -> dict[str, Any]:
    """Load the provisioned Grafana dashboard JSON."""
    loaded = json.loads(read_project_file(DASHBOARD_PATH))
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


def test_compose_declares_prometheus_and_grafana_services() -> None:
    """Docker Compose should include the local observability services and ports."""
    compose = read_project_file("docker-compose.yml")

    assert "  prometheus:" in compose
    assert "  grafana:" in compose
    assert '"${PROMETHEUS_HOST_PORT:-9090}:9090"' in compose
    assert '"${GRAFANA_HOST_PORT:-3000}:3000"' in compose
    assert "./observability/prometheus/prometheus.yml" in compose
    assert "./observability/grafana/provisioning" in compose
    assert "./observability/grafana/dashboards" in compose
    assert "prometheus_data:" in compose
    assert "grafana_data:" in compose


def test_prometheus_scrapes_api_metrics_endpoint_inside_compose() -> None:
    """Prometheus should scrape the API service through the Compose network."""
    prometheus_config = read_project_file("observability/prometheus/prometheus.yml")

    assert "scrape_interval: 15s" in prometheus_config
    assert "job_name: carbon-platform-api" in prometheus_config
    assert "metrics_path: /metrics" in prometheus_config
    assert "api:8000" in prometheus_config


def test_grafana_provisions_local_prometheus_datasource_and_dashboard() -> None:
    """Grafana provisioning should point to Prometheus and load dashboard JSON."""
    datasource_config = read_project_file(
        "observability/grafana/provisioning/datasources/prometheus.yml"
    )
    dashboard_provider_config = read_project_file(
        "observability/grafana/provisioning/dashboards/dashboards.yml"
    )

    assert "uid: local-prometheus" in datasource_config
    assert "url: http://prometheus:9090" in datasource_config
    assert "isDefault: true" in datasource_config
    assert "path: /var/lib/grafana/dashboards" in dashboard_provider_config
    assert "folder: Carbon Platform API" in dashboard_provider_config


def test_grafana_dashboard_json_is_valid_and_public_safe() -> None:
    """The provisioned dashboard should be valid JSON with local API panels."""
    dashboard = load_dashboard()
    panels = dashboard["panels"]
    panel_titles = {panel["title"] for panel in panels}
    expressions = "\n".join(
        target["expr"]
        for panel in panels
        for target in panel.get("targets", [])
        if "expr" in target
    )

    assert dashboard["title"] == "Carbon Platform API Local Overview"
    assert dashboard["uid"] == "carbon-api-local-overview"
    assert len(panels) >= 1
    assert "HTTP request rate by route" in panel_titles
    assert "p95 HTTP request duration" in panel_titles
    assert "carbon_api_http_requests_total" in expressions
    assert "carbon_api_http_request_duration_seconds_bucket" in expressions
    assert "process_resident_memory_bytes" in expressions
    assert all(
        panel["datasource"] == {"type": "prometheus", "uid": "local-prometheus"}
        for panel in panels
    )
