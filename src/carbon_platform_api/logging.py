"""Structured JSON logging helpers."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_JSON_HANDLER_MARKER = "_carbon_api_json_handler"
_RESERVED_LOG_RECORD_ATTRIBUTES = frozenset(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}


class JsonFormatter(logging.Formatter):
    """Format log records as compact JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Return a JSON representation of a log record."""
        log_event: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRIBUTES and not key.startswith("_"):
                log_event[key] = value

        if record.exc_info:
            log_event["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_event, default=str, separators=(",", ":"))


def configure_logging(log_level: str) -> None:
    """Configure root logging with a JSON stream handler."""
    level = logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    json_handler = _get_json_handler(root_logger)
    if json_handler is None:
        json_handler = logging.StreamHandler()
        setattr(json_handler, _JSON_HANDLER_MARKER, True)
        root_logger.addHandler(json_handler)

    json_handler.setLevel(level)
    json_handler.setFormatter(JsonFormatter())


def _get_json_handler(logger: logging.Logger) -> logging.Handler | None:
    """Return the project JSON handler if logging has already been configured."""
    for handler in logger.handlers:
        if getattr(handler, _JSON_HANDLER_MARKER, False):
            return handler
    return None
