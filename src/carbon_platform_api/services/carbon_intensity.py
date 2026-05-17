"""Service-level carbon intensity lookup orchestration."""

from __future__ import annotations

from datetime import datetime

from carbon_platform_api.cache.carbon_intensity import CarbonIntensityCacheProtocol
from carbon_platform_api.clients.carbon_intensity import CarbonIntensityClientProtocol
from carbon_platform_api.schemas.carbon_intensity import (
    CarbonIntensityQuery,
    CarbonIntensitySample,
)


class CarbonIntensityService:
    """Read carbon intensity samples from cache before consulting a provider."""

    def __init__(
        self,
        *,
        client: CarbonIntensityClientProtocol,
        cache: CarbonIntensityCacheProtocol,
        cache_ttl_seconds: int,
    ) -> None:
        """Create a service with injectable provider and cache implementations."""
        if cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds must be positive")
        self._client = client
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def get_intensity(
        self,
        *,
        region: str,
        start_time: datetime,
        end_time: datetime,
    ) -> CarbonIntensitySample:
        """Return a carbon intensity sample for a region/time window.

        Cache hits return without calling the external provider. Cache misses call
        the provider and store only successful provider responses.
        """
        query = CarbonIntensityQuery(
            region=region,
            start_time=start_time,
            end_time=end_time,
        )
        cached_sample = await self._cache.get(query)
        if cached_sample is not None:
            return cached_sample

        provider_sample = await self._client.fetch_intensity(query)
        await self._cache.set(
            query,
            provider_sample,
            ttl_seconds=self._cache_ttl_seconds,
        )
        return provider_sample
