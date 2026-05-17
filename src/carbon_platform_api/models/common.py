"""Shared model helpers."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time for Python-side timestamp defaults."""
    return datetime.now(UTC)
