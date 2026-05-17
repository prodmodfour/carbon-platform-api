"""API key authentication business service."""

from __future__ import annotations

import secrets
from collections.abc import Iterable


class ApiKeyAuthenticationError(PermissionError):
    """Raised when an API key is missing or invalid."""


class ApiKeyAuthService:
    """Validate API keys for protected business endpoints."""

    def __init__(self, *, auth_enabled: bool, api_keys: Iterable[str]) -> None:
        """Create the service with configured API keys.

        API keys are treated as opaque secret-like values. They are not logged by this
        service, and comparisons use ``secrets.compare_digest``.
        """
        self._auth_enabled = auth_enabled
        self._api_keys = tuple(api_key for api_key in api_keys if api_key)
        if self._auth_enabled and not self._api_keys:
            raise ValueError("At least one API key is required when auth is enabled.")

    def validate_api_key(self, api_key: str | None) -> None:
        """Validate an API key or no-op when authentication is disabled."""
        if not self._auth_enabled:
            return

        if not api_key:
            raise ApiKeyAuthenticationError

        is_valid = False
        for configured_api_key in self._api_keys:
            is_valid = secrets.compare_digest(api_key, configured_api_key) or is_valid

        if not is_valid:
            raise ApiKeyAuthenticationError
