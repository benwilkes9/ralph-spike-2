"""Shared test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from ralf_spike_2.database import close_db, init_db
from ralf_spike_2.main import app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import aiosqlite


@pytest.fixture
async def db() -> AsyncIterator[aiosqlite.Connection]:
    """Provide an in-memory database for each test."""
    conn = await init_db(":memory:")
    yield conn
    await close_db()


@pytest.fixture
async def client(db: aiosqlite.Connection) -> AsyncIterator[AsyncClient]:
    """Provide an HTTP test client with an in-memory database."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
