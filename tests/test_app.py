"""Tests for the FastAPI application scaffold."""

import pytest
from httpx import AsyncClient
from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncEngine


def _get_table_names(sync_conn: Connection) -> list[str]:
    return inspect(sync_conn).get_table_names()


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
