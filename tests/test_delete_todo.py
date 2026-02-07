"""Tests for DELETE /todos/{id} (Task 8)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def _create_todo(client: AsyncClient, title: str = "Buy milk") -> int:
    resp = await client.post("/todos", json={"title": title})
    return resp.json()["id"]


async def test_delete_existing_todo(client: AsyncClient) -> None:
    """Delete existing todo returns 204 with empty body."""
    todo_id = await _create_todo(client)
    resp = await client.delete(f"/todos/{todo_id}")
    assert resp.status_code == 204
    assert resp.content == b""


async def test_deleted_todo_not_retrievable(client: AsyncClient) -> None:
    """Todo is no longer retrievable after deletion."""
    todo_id = await _create_todo(client)
    await client.delete(f"/todos/{todo_id}")
    resp = await client.get(f"/todos/{todo_id}")
    assert resp.status_code == 404


async def test_delete_not_found(client: AsyncClient) -> None:
    """Delete non-existent id returns 404."""
    resp = await client.delete("/todos/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_delete_non_integer_id(client: AsyncClient) -> None:
    """Delete with non-integer id returns 422."""
    resp = await client.delete("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_deleted_id_never_reused(client: AsyncClient) -> None:
    """Deleted todo's id is never reused for new todos."""
    todo_id = await _create_todo(client, "First")
    await client.delete(f"/todos/{todo_id}")
    new_resp = await client.post("/todos", json={"title": "Second"})
    assert new_resp.status_code == 201
    assert new_resp.json()["id"] > todo_id
