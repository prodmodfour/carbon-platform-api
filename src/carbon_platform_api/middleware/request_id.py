"""Request ID middleware for correlation-friendly logs and responses."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_LOGGER_NAME = "carbon_platform_api.request"


class RequestIdMiddleware:
    """Attach a request ID to every HTTP response and completion log."""

    def __init__(self, app: ASGIApp, header_name: str = REQUEST_ID_HEADER) -> None:
        """Initialize the middleware."""
        self.app = app
        self.header_name = header_name
        self.logger = logging.getLogger(REQUEST_LOGGER_NAME)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an ASGI request and add request correlation metadata."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_headers = Headers(scope=scope)
        request_id = request_headers.get(self.header_name) or str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        method = str(scope.get("method", ""))
        path = str(scope.get("path", ""))
        status_code = 500
        start_time = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", status_code))
                response_headers = MutableHeaders(scope=message)
                response_headers[self.header_name] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            self.logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
