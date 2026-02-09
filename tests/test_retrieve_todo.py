"""Tests for GET /todos and GET /todos/{id} endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# GET /todos — list all
# ---------------------------------------------------------------------------


async def test_list_todos_empty(client: AsyncClient) -> None:
    """GET /todos with no todos returns 200 with []."""
    resp = await client.get("/todos")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_todos_returns_all_descending(client: AsyncClient) -> None:
    """GET /todos returns all todos ordered by descending id (newest first)."""
    await client.post("/todos", json={"title": "First"})
    await client.post("/todos", json={"title": "Second"})

    resp = await client.get("/todos")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "Second"
    assert data[1]["title"] == "First"
    assert data[0]["id"] > data[1]["id"]


async def test_list_todos_three_items_reverse_order(client: AsyncClient) -> None:
    """Create 3 todos; GET /todos returns them in reverse creation order."""
    await client.post("/todos", json={"title": "Alpha"})
    await client.post("/todos", json={"title": "Beta"})
    await client.post("/todos", json={"title": "Gamma"})

    resp = await client.get("/todos")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    titles = [item["title"] for item in data]
    assert titles == ["Gamma", "Beta", "Alpha"]


async def test_list_todos_response_is_plain_array(client: AsyncClient) -> None:
    """Response body for list is a plain JSON array (not an envelope)."""
    resp = await client.get("/todos")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GET /todos/{id} — single item
# ---------------------------------------------------------------------------


async def test_get_todo_success(client: AsyncClient) -> None:
    """GET /todos/1 returns 200 with the correct todo object."""
    create_resp = await client.post("/todos", json={"title": "Find me"})
    todo_id = create_resp.json()["id"]

    resp = await client.get(f"/todos/{todo_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == todo_id
    assert data["title"] == "Find me"
    assert data["completed"] is False


async def test_get_todo_not_found(client: AsyncClient) -> None:
    """GET /todos/999 returns 404 'Todo not found'."""
    resp = await client.get("/todos/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_get_todo_invalid_id_string(client: AsyncClient) -> None:
    """GET /todos/abc returns 422 'id must be a positive integer'."""
    resp = await client.get("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_get_todo_id_zero(client: AsyncClient) -> None:
    """GET /todos/0 returns 422 'id must be a positive integer'."""
    resp = await client.get("/todos/0")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_get_todo_negative_id(client: AsyncClient) -> None:
    """GET /todos/-1 returns 422 'id must be a positive integer'."""
    resp = await client.get("/todos/-1")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"
