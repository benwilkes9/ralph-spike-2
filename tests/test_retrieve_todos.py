"""Tests for GET /todos and GET /todos/{id} (Task 4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_list_todos_returns_all_newest_first(client: AsyncClient) -> None:
    """GET /todos returns 200 with all todos, newest first."""
    await client.post("/todos", json={"title": "First"})
    await client.post("/todos", json={"title": "Second"})
    await client.post("/todos", json={"title": "Third"})

    resp = await client.get("/todos")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["title"] == "Third"
    assert data[1]["title"] == "Second"
    assert data[2]["title"] == "First"


async def test_list_todos_empty(client: AsyncClient) -> None:
    """GET /todos returns 200 with [] when no todos exist."""
    resp = await client.get("/todos")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_todo_by_id(client: AsyncClient) -> None:
    """GET /todos/{id} returns 200 with matching todo."""
    create_resp = await client.post("/todos", json={"title": "Buy milk"})
    todo_id = create_resp.json()["id"]

    resp = await client.get(f"/todos/{todo_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == todo_id
    assert data["title"] == "Buy milk"
    assert data["completed"] is False


async def test_get_todo_not_found(client: AsyncClient) -> None:
    """GET /todos/{id} with non-existent id returns 404."""
    resp = await client.get("/todos/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_get_todo_non_integer_id(client: AsyncClient) -> None:
    """GET /todos/{id} with non-integer id returns 422."""
    resp = await client.get("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_get_todo_zero_id(client: AsyncClient) -> None:
    """GET /todos/{id} with zero id returns 422."""
    resp = await client.get("/todos/0")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_get_todo_negative_id(client: AsyncClient) -> None:
    """GET /todos/{id} with negative id returns 422."""
    resp = await client.get("/todos/-1")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"
