"""Tests for GET /todos and GET /todos/{id} endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_todos_empty(client: AsyncClient) -> None:
    """GET /todos returns 200 with an empty array when no todos exist."""
    resp = await client.get("/todos")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_todos_ordered_desc(
    client: AsyncClient,
    sample_todos: list[dict[str, Any]],
) -> None:
    """GET /todos returns all todos ordered by descending id."""
    resp = await client.get("/todos")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    ids = [t["id"] for t in data]
    assert ids == sorted(ids, reverse=True)


@pytest.mark.asyncio
async def test_list_todos_newest_first(client: AsyncClient) -> None:
    """After creating multiple todos, the list is newest-first."""
    await client.post("/todos", json={"title": "First"})
    await client.post("/todos", json={"title": "Second"})
    await client.post("/todos", json={"title": "Third"})
    resp = await client.get("/todos")
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Third", "Second", "First"]


@pytest.mark.asyncio
async def test_get_todo_by_id(
    client: AsyncClient,
    sample_todos: list[dict[str, Any]],
) -> None:
    """GET /todos/{id} returns the matching todo object."""
    todo_id = sample_todos[0]["id"]
    resp = await client.get(f"/todos/{todo_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id
    assert resp.json()["title"] == sample_todos[0]["title"]


@pytest.mark.asyncio
async def test_get_todo_not_found(client: AsyncClient) -> None:
    """GET /todos/{id} for a non-existent id returns 404."""
    resp = await client.get("/todos/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


@pytest.mark.asyncio
async def test_get_todo_non_integer_id(client: AsyncClient) -> None:
    """GET /todos/{id} with a non-integer id returns 422."""
    resp = await client.get("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_get_todo_zero_id(client: AsyncClient) -> None:
    """GET /todos/{id} with zero returns 422."""
    resp = await client.get("/todos/0")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_get_todo_negative_id(client: AsyncClient) -> None:
    """GET /todos/{id} with a negative number returns 422."""
    resp = await client.get("/todos/-1")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"
