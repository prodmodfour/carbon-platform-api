"""Metrics rendering service."""

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

PROMETHEUS_TEXT_CONTENT_TYPE = CONTENT_TYPE_LATEST


class MetricsService:
    """Render application metrics from a Prometheus registry."""

    def __init__(self, registry: CollectorRegistry) -> None:
        """Create a metrics service with an externally managed registry."""
        self._registry = registry

    def render_prometheus_text(self) -> bytes:
        """Return metrics in Prometheus text exposition format."""
        return generate_latest(self._registry)
