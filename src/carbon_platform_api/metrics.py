"""Prometheus metrics registry and recorders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from prometheus_client import CollectorRegistry, Counter, Histogram
from prometheus_client.gc_collector import GCCollector
from prometheus_client.platform_collector import PlatformCollector
from prometheus_client.process_collector import ProcessCollector


class HttpMetricsRecorderProtocol(Protocol):
    """Small interface required by HTTP metrics middleware."""

    def record_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record one completed HTTP request."""
        ...


@dataclass(frozen=True)
class PrometheusMetrics:
    """Application metrics bound to an isolated Prometheus registry."""

    registry: CollectorRegistry
    http_recorder: HttpMetricsRecorderProtocol


class PrometheusHttpMetricsRecorder:
    """Record HTTP request counts and latency in Prometheus format."""

    def __init__(self, registry: CollectorRegistry) -> None:
        """Create HTTP metrics registered against the supplied registry."""
        self._request_counter = Counter(
            "carbon_api_http_requests_total",
            "Total HTTP requests handled by the API.",
            labelnames=("method", "path", "status_code"),
            registry=registry,
        )
        self._request_duration = Histogram(
            "carbon_api_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            labelnames=("method", "path", "status_code"),
            registry=registry,
        )

    def record_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record one completed HTTP request."""
        normalized_method = method.upper() if method else "UNKNOWN"
        normalized_path = path or "unknown"
        status_label = str(status_code)
        self._request_counter.labels(
            method=normalized_method,
            path=normalized_path,
            status_code=status_label,
        ).inc()
        self._request_duration.labels(
            method=normalized_method,
            path=normalized_path,
            status_code=status_label,
        ).observe(duration_seconds)


def create_prometheus_metrics() -> PrometheusMetrics:
    """Create an isolated registry with process and application metrics."""
    registry = CollectorRegistry()
    ProcessCollector(registry=registry)
    PlatformCollector(registry=registry)
    GCCollector(registry=registry)
    return PrometheusMetrics(
        registry=registry,
        http_recorder=PrometheusHttpMetricsRecorder(registry),
    )
