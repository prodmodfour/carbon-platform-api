"""Async SQLAlchemy engine and session factory helpers."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_database_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine for the configured database URL."""
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory with explicit transaction ownership."""
    return async_sessionmaker(engine, expire_on_commit=False)
