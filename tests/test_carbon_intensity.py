"""Tests for carbon intensity provider, cache, and service behaviour."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from carbon_platform_api.cache.carbon_intensity import (
    RedisCarbonIntensityCache,
    deserialize_carbon_intensity_sample,
    serialize_carbon_intensity_sample,
)
from carbon_platform_api.clients.carbon_intensity import (
    CarbonIntensityProviderError,
    CarbonIntensityProviderResponseError,
    CarbonIntensityProviderTimeoutError,
    HttpCarbonIntensityClient,
)
from carbon_platform_api.schemas.carbon_intensity import (
    CarbonIntensityQuery,
    CarbonIntensitySample,
)
from carbon_platform_api.services.carbon_intensity import CarbonIntensityService

_START_TIME = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
_END_TIME = _START_TIME + timedelta(hours=1)


def sample_query() -> CarbonIntensityQuery:
    """Build a deterministic public-safe carbon intensity query."""
    return CarbonIntensityQuery(
        region=" sample-region-1 ",
        start_time=_START_TIME,
        end_time=_END_TIME,
    )


def sample_intensity(*, source: str = "sample-provider") -> CarbonIntensitySample:
    """Build a deterministic public-safe carbon intensity sample."""
    return CarbonIntensitySample(
        region=" sample-region-1 ",
        measured_at=_START_TIME,
        grams_co2e_per_kwh=Decimal("321.1234"),
        source=source,
    )


class FakeCarbonIntensityClient:
    """Fake provider client for service-level tests."""

    def __init__(
        self,
        *,
        sample: CarbonIntensitySample | None = None,
        error: Exception | None = None,
    ) -> None:
        self._sample = sample
        self._error = error
        self.calls: list[CarbonIntensityQuery] = []

    async def fetch_intensity(
        self,
        query: CarbonIntensityQuery,
    ) -> CarbonIntensitySample:
        """Return a configured sample or raise a configured error."""
        self.calls.append(query)
        if self._error is not None:
            raise self._error
        assert self._sample is not None
        return self._sample


CacheKey = tuple[str, datetime, datetime]


class FakeCarbonIntensityCache:
    """Fake cache for service-level tests."""

    def __init__(self) -> None:
        self.samples: dict[CacheKey, CarbonIntensitySample] = {}
        self.get_calls: list[CarbonIntensityQuery] = []
        self.set_calls: list[
            tuple[CarbonIntensityQuery, CarbonIntensitySample, int]
        ] = []

    async def get(
        self,
        query: CarbonIntensityQuery,
    ) -> CarbonIntensitySample | None:
        """Return a sample from in-memory cache."""
        self.get_calls.append(query)
        return self.samples.get(_cache_key(query))

    async def set(
        self,
        query: CarbonIntensityQuery,
        sample: CarbonIntensitySample,
        *,
        ttl_seconds: int,
    ) -> None:
        """Store a sample in in-memory cache."""
        self.set_calls.append((query, sample, ttl_seconds))
        self.samples[_cache_key(query)] = sample


class FakeRedisCommandClient:
    """Small fake Redis command client for serialization tests."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.expirations: dict[str, int] = {}
        self.closed = False

    async def get(self, name: str) -> str | bytes | None:
        """Return a stored Redis value."""
        return self.data.get(name)

    async def set(self, name: str, value: str, *, ex: int) -> object:
        """Store a Redis value and record its expiration."""
        self.data[name] = value
        self.expirations[name] = ex
        return True

    async def aclose(self) -> None:
        """Record that the fake client was closed."""
        self.closed = True


def test_carbon_intensity_service_returns_cache_hit_without_provider_call() -> None:
    """Cache hits should bypass the external provider."""
    asyncio.run(_exercise_cache_hit())


async def _exercise_cache_hit() -> None:
    query = sample_query()
    cached_sample = sample_intensity(source="sample-cache")
    cache = FakeCarbonIntensityCache()
    cache.samples[_cache_key(query)] = cached_sample
    client = FakeCarbonIntensityClient(
        error=AssertionError("provider should not be called on cache hit")
    )
    service = CarbonIntensityService(
        client=client,
        cache=cache,
        cache_ttl_seconds=300,
    )

    result = await service.get_intensity(
        region=query.region,
        start_time=query.start_time,
        end_time=query.end_time,
    )

    assert result == cached_sample
    assert client.calls == []
    assert cache.set_calls == []


def test_carbon_intensity_service_fetches_and_caches_on_miss() -> None:
    """Cache misses should call the provider and store successful responses."""
    asyncio.run(_exercise_cache_miss())


async def _exercise_cache_miss() -> None:
    provider_sample = sample_intensity()
    cache = FakeCarbonIntensityCache()
    client = FakeCarbonIntensityClient(sample=provider_sample)
    service = CarbonIntensityService(
        client=client,
        cache=cache,
        cache_ttl_seconds=600,
    )

    result = await service.get_intensity(
        region=" sample-region-1 ",
        start_time=_START_TIME,
        end_time=_END_TIME,
    )

    assert result == provider_sample
    assert len(client.calls) == 1
    assert client.calls[0].region == "sample-region-1"
    assert cache.set_calls == [(client.calls[0], provider_sample, 600)]
    assert cache.samples[_cache_key(client.calls[0])] == provider_sample


@pytest.mark.parametrize(
    "error",
    [
        CarbonIntensityProviderError("provider unavailable"),
        CarbonIntensityProviderTimeoutError("provider timed out"),
    ],
)
def test_carbon_intensity_service_does_not_cache_provider_failures(
    error: Exception,
) -> None:
    """Failed provider calls should propagate and should not be cached."""
    asyncio.run(_exercise_provider_failure(error))


async def _exercise_provider_failure(error: Exception) -> None:
    cache = FakeCarbonIntensityCache()
    client = FakeCarbonIntensityClient(error=error)
    service = CarbonIntensityService(
        client=client,
        cache=cache,
        cache_ttl_seconds=600,
    )

    with pytest.raises(type(error)):
        await service.get_intensity(
            region="sample-region-1",
            start_time=_START_TIME,
            end_time=_END_TIME,
        )

    assert len(client.calls) == 1
    assert cache.set_calls == []
    assert cache.samples == {}


def test_redis_cache_serializes_and_deserializes_carbon_intensity_samples() -> None:
    """Redis cache should round-trip carbon intensity samples as JSON."""
    asyncio.run(_exercise_redis_cache_serialization())


async def _exercise_redis_cache_serialization() -> None:
    redis_client = FakeRedisCommandClient()
    cache = RedisCarbonIntensityCache(redis_client, key_prefix="test-intensity")
    query = sample_query()
    sample = sample_intensity()

    await cache.set(query, sample, ttl_seconds=123)
    result = await cache.get(query)

    assert result == sample
    assert redis_client.expirations == {next(iter(redis_client.data)): 123}
    stored_payload = next(iter(redis_client.data.values()))
    assert deserialize_carbon_intensity_sample(stored_payload) == sample
    assert serialize_carbon_intensity_sample(sample) == stored_payload


def test_http_carbon_intensity_client_parses_successful_response() -> None:
    """HTTP client should map a valid public-safe response into a sample."""
    asyncio.run(_exercise_http_client_success())


async def _exercise_http_client_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/intensity"
        assert request.url.params["region"] == "sample-region-1"
        assert request.url.params["start_time"] == "2026-01-01T00:00:00Z"
        assert request.url.params["end_time"] == "2026-01-01T01:00:00Z"
        return httpx.Response(
            200,
            json={
                "region": "sample-region-1",
                "measured_at": "2026-01-01T00:00:00Z",
                "grams_co2e_per_kwh": "321.1234",
                "source": "sample-provider",
            },
        )

    client = HttpCarbonIntensityClient(
        base_url="https://carbon-intensity.example.invalid",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_intensity(sample_query())

    assert result == sample_intensity()


def test_http_carbon_intensity_client_maps_provider_failure() -> None:
    """HTTP provider errors should be translated to client-level failures."""
    asyncio.run(_exercise_http_client_provider_failure())


async def _exercise_http_client_provider_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "sample outage"})

    client = HttpCarbonIntensityClient(
        base_url="https://carbon-intensity.example.invalid",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CarbonIntensityProviderError, match="HTTP 503"):
        await client.fetch_intensity(sample_query())


def test_http_carbon_intensity_client_maps_timeout() -> None:
    """HTTP timeouts should be translated to timeout-specific failures."""
    asyncio.run(_exercise_http_client_timeout())


async def _exercise_http_client_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sample timeout", request=request)

    client = HttpCarbonIntensityClient(
        base_url="https://carbon-intensity.example.invalid",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CarbonIntensityProviderTimeoutError):
        await client.fetch_intensity(sample_query())


def test_http_carbon_intensity_client_rejects_invalid_payload() -> None:
    """Invalid provider payloads should not leak through the client boundary."""
    asyncio.run(_exercise_http_client_invalid_payload())


async def _exercise_http_client_invalid_payload() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"region": "sample-region-1"})

    client = HttpCarbonIntensityClient(
        base_url="https://carbon-intensity.example.invalid",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CarbonIntensityProviderResponseError):
        await client.fetch_intensity(sample_query())


def _cache_key(query: CarbonIntensityQuery) -> CacheKey:
    return (query.region, query.start_time, query.end_time)
