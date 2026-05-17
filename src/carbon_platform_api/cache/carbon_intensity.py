"""Redis-backed cache abstraction for carbon intensity samples."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast
from urllib.parse import quote

import redis.asyncio as redis
from pydantic import ValidationError

from carbon_platform_api.schemas.carbon_intensity import (
    CarbonIntensityQuery,
    CarbonIntensitySample,
)


class CarbonIntensityCacheSerializationError(ValueError):
    """Raised when a cached carbon intensity payload cannot be decoded."""


class RedisCommandClientProtocol(Protocol):
    """Small subset of Redis commands required by the cache implementation."""

    async def get(self, name: str) -> str | bytes | None:
        """Return a cached value by key."""
        ...

    async def set(self, name: str, value: str, *, ex: int) -> object:
        """Store a cached value with a second-based expiration."""
        ...

    async def aclose(self) -> None:
        """Close the Redis client connection pool."""
        ...


class CarbonIntensityCacheProtocol(Protocol):
    """Cache operations required by the carbon intensity service."""

    async def get(
        self,
        query: CarbonIntensityQuery,
    ) -> CarbonIntensitySample | None:
        """Return a cached sample for the query, if present."""
        ...

    async def set(
        self,
        query: CarbonIntensityQuery,
        sample: CarbonIntensitySample,
        *,
        ttl_seconds: int,
    ) -> None:
        """Store a sample for the query with a second-based TTL."""
        ...


class RedisCarbonIntensityCache:
    """Redis implementation of carbon intensity sample caching."""

    def __init__(
        self,
        redis_client: RedisCommandClientProtocol,
        *,
        key_prefix: str = "carbon-intensity",
    ) -> None:
        """Create a Redis cache using an externally managed Redis client."""
        normalized_prefix = key_prefix.strip()
        if not normalized_prefix:
            raise ValueError("key_prefix must not be blank")
        self._redis_client = redis_client
        self._key_prefix = normalized_prefix

    async def get(
        self,
        query: CarbonIntensityQuery,
    ) -> CarbonIntensitySample | None:
        """Return a cached sample for the query, if Redis contains one."""
        raw_payload = await self._redis_client.get(self._cache_key(query))
        if raw_payload is None:
            return None
        return deserialize_carbon_intensity_sample(raw_payload)

    async def set(
        self,
        query: CarbonIntensityQuery,
        sample: CarbonIntensitySample,
        *,
        ttl_seconds: int,
    ) -> None:
        """Store a sample for the query with a positive TTL."""
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        await self._redis_client.set(
            self._cache_key(query),
            serialize_carbon_intensity_sample(sample),
            ex=ttl_seconds,
        )

    def _cache_key(self, query: CarbonIntensityQuery) -> str:
        encoded_region = quote(query.region, safe="")
        return ":".join(
            (
                self._key_prefix,
                "v1",
                encoded_region,
                _format_cache_timestamp(query.start_time),
                _format_cache_timestamp(query.end_time),
            )
        )


def create_redis_client(redis_url: str) -> RedisCommandClientProtocol:
    """Create an async Redis client for application cache implementations."""
    normalized_redis_url = redis_url.strip()
    if not normalized_redis_url:
        raise ValueError("redis_url must not be blank")
    return cast(
        RedisCommandClientProtocol,
        redis.from_url(  # type: ignore[no-untyped-call]
            normalized_redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        ),
    )


def serialize_carbon_intensity_sample(sample: CarbonIntensitySample) -> str:
    """Serialize a carbon intensity sample for Redis storage."""
    return sample.model_dump_json()


def deserialize_carbon_intensity_sample(
    payload: str | bytes,
) -> CarbonIntensitySample:
    """Deserialize a Redis payload into a carbon intensity sample."""
    if isinstance(payload, bytes):
        normalized_payload = payload.decode("utf-8")
    else:
        normalized_payload = payload

    try:
        return CarbonIntensitySample.model_validate_json(normalized_payload)
    except (ValidationError, ValueError) as exc:
        raise CarbonIntensityCacheSerializationError(
            "Cached carbon intensity payload is invalid."
        ) from exc


def _format_cache_timestamp(value: datetime) -> str:
    """Serialize timestamps in stable UTC form for cache keys."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
