"""Async SQLAlchemy engine and session management for SQLite."""

import os

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ralf_spike_2.models import Base

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./todos.db"


def get_database_url() -> str:
    """Return the database URL from environment or default."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    url = database_url or get_database_url()
    return create_async_engine(url, echo=False)


def create_session_factory(
    engine: AsyncEngine,
) -> sessionmaker[AsyncSession]:  # type: ignore[type-var]
    """Create an async session factory bound to the given engine."""
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]


async def create_tables(engine: AsyncEngine) -> None:
    """Create all tables defined in the ORM metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
