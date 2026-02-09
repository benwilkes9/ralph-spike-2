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
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_zero_id(client: AsyncClient) -> None:
    """Deleting with zero id returns 422."""
    resp = await client.delete("/todos/0")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_negative_id(client: AsyncClient) -> None:
    """Deleting with negative id returns 422."""
    resp = await client.delete("/todos/-1")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_deleted_id_not_reused(client: AsyncClient) -> None:
    """The deleted todo's id is never reused."""
    r1 = await client.post("/todos", json={"title": "Only one"})
    only_id = r1.json()["id"]
    await client.delete(f"/todos/{only_id}")
    r2 = await client.post("/todos", json={"title": "After delete"})
    assert r2.json()["id"] > only_id


@pytest.mark.asyncio
async def test_deleted_title_reusable_case_insensitive(
    client: AsyncClient,
) -> None:
    """After deletion, the title can be reused with different casing."""
    r = await client.post("/todos", json={"title": "Buy Milk"})
    await client.delete(f"/todos/{r.json()['id']}")
    resp = await client.post("/todos", json={"title": "buy milk"})
    assert resp.status_code == 201
    assert resp.json()["title"] == "buy milk"


@pytest.mark.asyncio
async def test_put_reuse_deleted_title(client: AsyncClient) -> None:
    """PUT can reuse a title from a deleted todo."""
    r1 = await client.post("/todos", json={"title": "Deleted Title"})
    await client.delete(f"/todos/{r1.json()['id']}")
    r2 = await client.post("/todos", json={"title": "Other"})
    resp = await client.put(
        f"/todos/{r2.json()['id']}",
        json={"title": "Deleted Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Deleted Title"


@pytest.mark.asyncio
async def test_patch_reuse_deleted_title(client: AsyncClient) -> None:
    """PATCH can reuse a title from a deleted todo."""
    r1 = await client.post("/todos", json={"title": "Deleted Title"})
    await client.delete(f"/todos/{r1.json()['id']}")
    r2 = await client.post("/todos", json={"title": "Other"})
    resp = await client.patch(
        f"/todos/{r2.json()['id']}",
        json={"title": "Deleted Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Deleted Title"
