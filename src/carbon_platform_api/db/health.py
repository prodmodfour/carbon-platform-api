"""Database readiness checks."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseReadinessCheck:
    """Check PostgreSQL connectivity through an async SQLAlchemy engine."""

    name = "database"

    def __init__(self, engine: AsyncEngine) -> None:
        """Create a database readiness check with an externally managed engine."""
        self._engine = engine

    async def check(self) -> None:
        """Run a lightweight connectivity query."""
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
