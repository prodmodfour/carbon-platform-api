"""HTTP request metrics middleware."""

from __future__ import annotations

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from carbon_platform_api.metrics import HttpMetricsRecorderProtocol


class RequestMetricsMiddleware:
    """Record Prometheus-compatible metrics for completed HTTP requests."""

    def __init__(
        self,
        app: ASGIApp,
        recorder: HttpMetricsRecorderProtocol,
    ) -> None:
        """Initialize the middleware."""
        self.app = app
        self._recorder = recorder

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Record request count and duration for each HTTP request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", ""))
        status_code = 500
        start_time = time.perf_counter()

        async def send_with_status_capture(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", status_code))
            await send(message)

        try:
            await self.app(scope, receive, send_with_status_capture)
        finally:
            duration_seconds = time.perf_counter() - start_time
            self._recorder.record_request(
                method=method,
                path=_request_path(scope),
                status_code=status_code,
                duration_seconds=duration_seconds,
            )


def _request_path(scope: Scope) -> str:
    """Return the matched route path when available to avoid ID cardinality."""
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return str(scope.get("path", "unknown"))
