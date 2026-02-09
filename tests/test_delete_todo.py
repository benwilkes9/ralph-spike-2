"""Tests for DELETE /todos/{id} endpoint."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------


async def test_delete_existing_todo_returns_204(client: AsyncClient) -> None:
    """Delete an existing todo returns 204 with empty body."""
    create_resp = await client.post("/todos", json={"title": "To delete"})
    todo_id = create_resp.json()["id"]

    resp = await client.delete(f"/todos/{todo_id}")
    assert resp.status_code == 204
    assert resp.content == b""


async def test_deleted_todo_not_retrievable(client: AsyncClient) -> None:
    """The deleted todo is no longer retrievable (GET /todos/{id} returns 404)."""
    create_resp = await client.post("/todos", json={"title": "Will vanish"})
    todo_id = create_resp.json()["id"]

    await client.delete(f"/todos/{todo_id}")

    resp = await client.get(f"/todos/{todo_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_deleted_todo_not_in_list(client: AsyncClient) -> None:
    """The deleted todo does not appear in GET /todos list."""
    create_resp = await client.post("/todos", json={"title": "Disappears"})
    todo_id = create_resp.json()["id"]

    await client.delete(f"/todos/{todo_id}")

    resp = await client.get("/todos")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert todo_id not in ids


async def test_delete_same_id_twice(client: AsyncClient) -> None:
    """Delete the same id twice: first returns 204, second returns 404."""
    create_resp = await client.post("/todos", json={"title": "Once only"})
    todo_id = create_resp.json()["id"]

    first = await client.delete(f"/todos/{todo_id}")
    assert first.status_code == 204

    second = await client.delete(f"/todos/{todo_id}")
    assert second.status_code == 404
    assert second.json()["detail"] == "Todo not found"


async def test_deleted_id_not_reused(client: AsyncClient) -> None:
    """Deleted id is never reused (create new todo after delete, its id is higher)."""
    create_resp = await client.post("/todos", json={"title": "Old item"})
    old_id = create_resp.json()["id"]

    await client.delete(f"/todos/{old_id}")

    new_resp = await client.post("/todos", json={"title": "New item"})
    new_id = new_resp.json()["id"]
    assert new_id > old_id


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


async def test_delete_nonexistent_id(client: AsyncClient) -> None:
    """Delete non-existent id returns 404 'Todo not found'."""
    resp = await client.delete("/todos/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_delete_non_integer_id(client: AsyncClient) -> None:
    """Delete non-integer id returns 422 'id must be a positive integer'."""
    resp = await client.delete("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_delete_zero_id(client: AsyncClient) -> None:
    """Delete id=0 returns 422 'id must be a positive integer'."""
    resp = await client.delete("/todos/0")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_delete_negative_id(client: AsyncClient) -> None:
    """Delete id=-1 returns 422 'id must be a positive integer'."""
    resp = await client.delete("/todos/-1")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"
