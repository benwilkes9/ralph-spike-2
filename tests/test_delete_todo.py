"""Tests for DELETE /todos/{id} endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_existing_todo(client: AsyncClient) -> None:
    """Deleting an existing todo returns 204 with no response body."""
    r = await client.post("/todos", json={"title": "Delete me"})
    todo_id = r.json()["id"]
    resp = await client.delete(f"/todos/{todo_id}")
    assert resp.status_code == 204
    assert resp.content == b""


@pytest.mark.asyncio
async def test_deleted_todo_not_retrievable(client: AsyncClient) -> None:
    """The deleted todo is no longer retrievable via GET."""
    r = await client.post("/todos", json={"title": "Delete me"})
    todo_id = r.json()["id"]
    await client.delete(f"/todos/{todo_id}")
    resp = await client.get(f"/todos/{todo_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deleted_title_reusable(client: AsyncClient) -> None:
    """The deleted todo's title can be reused."""
    r = await client.post("/todos", json={"title": "Reuse me"})
    todo_id = r.json()["id"]
    await client.delete(f"/todos/{todo_id}")
    resp = await client.post("/todos", json={"title": "Reuse me"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_delete_not_found(client: AsyncClient) -> None:
    """Deleting a non-existent id returns 404."""
    resp = await client.delete("/todos/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


@pytest.mark.asyncio
async def test_delete_non_integer_id(client: AsyncClient) -> None:
    """Deleting with a non-integer id returns 422."""
    resp = await client.delete("/todos/abc")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_zero_id(client: AsyncClient) -> None:
    """Deleting with zero id returns 422."""
    resp = await client.delete("/todos/0")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_negative_id(client: AsyncClient) -> None:
    """Deleting with negative id returns 422."""
    resp = await client.delete("/todos/-1")
    assert resp.status_code == 422
