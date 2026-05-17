"""Mockable HTTP client for carbon intensity provider lookups."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import httpx
from pydantic import ValidationError

from carbon_platform_api.schemas.carbon_intensity import (
    CarbonIntensityQuery,
    CarbonIntensitySample,
)


class CarbonIntensityClientError(RuntimeError):
    """Base class for carbon intensity client failures."""


class CarbonIntensityProviderError(CarbonIntensityClientError):
    """Raised when the provider request fails."""


class CarbonIntensityProviderTimeoutError(CarbonIntensityProviderError):
    """Raised when the provider request times out."""


class CarbonIntensityProviderResponseError(CarbonIntensityProviderError):
    """Raised when the provider returns an invalid response payload."""


class CarbonIntensityClientProtocol(Protocol):
    """Small provider interface required by carbon intensity services."""

    async def fetch_intensity(
        self,
        query: CarbonIntensityQuery,
    ) -> CarbonIntensitySample:
        """Fetch one carbon intensity sample for the query window."""
        ...


class HttpCarbonIntensityClient:
    """HTTP implementation of the carbon intensity provider client.

    The expected public-safe demo response shape is::

        {
          "region": "sample-region-1",
          "measured_at": "2026-01-01T00:00:00Z",
          "grams_co2e_per_kwh": "350.0",
          "source": "sample-provider"
        }

    The default base URL is configured to a ``.invalid`` host so local tests and
    examples never depend on a live third-party service.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Create an HTTP provider client with injectable transport for tests."""
        normalized_base_url = base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise ValueError("base_url must not be blank")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self._base_url = normalized_base_url
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def fetch_intensity(
        self,
        query: CarbonIntensityQuery,
    ) -> CarbonIntensitySample:
        """Fetch carbon intensity for a region/time window."""
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    "/intensity",
                    params={
                        "region": query.region,
                        "start_time": _format_timestamp(query.start_time),
                        "end_time": _format_timestamp(query.end_time),
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise CarbonIntensityProviderTimeoutError(
                "Carbon intensity provider request timed out."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise CarbonIntensityProviderError(
                f"Carbon intensity provider returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise CarbonIntensityProviderError(
                "Carbon intensity provider request failed."
            ) from exc

        try:
            payload: object = response.json()
        except ValueError as exc:
            raise CarbonIntensityProviderResponseError(
                "Carbon intensity provider returned invalid JSON."
            ) from exc

        try:
            return CarbonIntensitySample.model_validate(payload)
        except ValidationError as exc:
            raise CarbonIntensityProviderResponseError(
                "Carbon intensity provider returned an invalid payload."
            ) from exc


def _format_timestamp(value: datetime) -> str:
    """Serialize timestamps in stable UTC ISO-8601 form for provider queries."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
