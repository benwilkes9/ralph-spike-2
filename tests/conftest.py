"""Test fixtures for the Todo API."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ralf_spike_2.database import get_session
from ralf_spike_2.main import app
from ralf_spike_2.models import Base


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test async engine with in-memory SQLite."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create a test async session."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def client(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client using the test database."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_todos(
    client: AsyncClient,
) -> AsyncGenerator[list[dict[str, Any]], None]:
    """Create sample todos for tests that need pre-existing data."""
    todos: list[dict[str, Any]] = []
    for title in ["Buy milk", "Walk the dog", "Read a book"]:
        resp = await client.post("/todos", json={"title": title})
        todos.append(resp.json())
    yield todos
