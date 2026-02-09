"""Tests for the FastAPI application scaffold."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from ralf_spike_2.app import app
from ralf_spike_2.database import create_engine, create_tables

IN_MEMORY_URL = "sqlite+aiosqlite:///:memory:"


def _get_table_names(sync_conn: Connection) -> list[str]:
    return inspect(sync_conn).get_table_names()


@pytest_asyncio.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create an in-memory engine with tables for testing."""
    eng = create_engine(IN_MEMORY_URL)
    await create_tables(eng)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Create a test HTTP client bound to the FastAPI app."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_returns_200_ok(client: AsyncClient) -> None:
    """GET /health returns 200 with {"status": "ok"}."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_startup_creates_todos_table(test_engine: AsyncEngine) -> None:
    """App startup (via create_tables) creates the todos table in the database."""
    async with test_engine.connect() as conn:
        table_names = await conn.run_sync(_get_table_names)
    assert "todos" in table_names


@pytest.mark.asyncio
async def test_client_fixture_is_functional(client: AsyncClient) -> None:
    """The test client fixture can make requests to the app."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
