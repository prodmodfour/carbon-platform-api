"""Redis readiness checks."""

from typing import Protocol


class RedisHealthClientProtocol(Protocol):
    """Small Redis command subset required for readiness checks."""

    async def ping(self) -> bool:
        """Return whether Redis responds to a ping command."""
        ...


class RedisReadinessError(RuntimeError):
    """Raised when Redis responds to ping with an unhealthy result."""


class RedisReadinessCheck:
    """Check Redis connectivity through an externally managed client."""

    name = "redis"

    def __init__(self, redis_client: RedisHealthClientProtocol) -> None:
        """Create a Redis readiness check."""
        self._redis_client = redis_client

    async def check(self) -> None:
        """Ping Redis and fail when the ping response is not successful."""
        if not await self._redis_client.ping():
            raise RedisReadinessError("Redis ping returned an unhealthy result.")
