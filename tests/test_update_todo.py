"""Tests for PUT /todos/{id} (Task 5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def _create_todo(client: AsyncClient, title: str = "Buy milk") -> int:
    resp = await client.post("/todos", json={"title": title})
    return resp.json()["id"]


async def test_put_replaces_title_and_completed(client: AsyncClient) -> None:
    """PUT replaces title and completed."""
    todo_id = await _create_todo(client)
    resp = await client.put(
        f"/todos/{todo_id}", json={"title": "Buy eggs", "completed": True}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Buy eggs"
    assert data["completed"] is True


async def test_put_omitting_completed_resets_to_false(client: AsyncClient) -> None:
    """Omitting completed resets it to false."""
    todo_id = await _create_todo(client)
    # First set completed to true
    await client.put(f"/todos/{todo_id}", json={"title": "Buy milk", "completed": True})
    # Then PUT without completed
    resp = await client.put(f"/todos/{todo_id}", json={"title": "Buy milk"})
    assert resp.status_code == 200
    assert resp.json()["completed"] is False


async def test_put_missing_title(client: AsyncClient) -> None:
    """Missing title returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.put(f"/todos/{todo_id}", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


async def test_put_blank_title(client: AsyncClient) -> None:
    """Blank title returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.put(f"/todos/{todo_id}", json={"title": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


async def test_put_whitespace_title(client: AsyncClient) -> None:
    """Whitespace-only title returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.put(f"/todos/{todo_id}", json={"title": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


async def test_put_title_too_long(client: AsyncClient) -> None:
    """Title > 500 chars returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.put(f"/todos/{todo_id}", json={"title": "x" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


async def test_put_duplicate_title(client: AsyncClient) -> None:
    """Duplicate title (different todo) returns 409."""
    await _create_todo(client, "First")
    todo_id = await _create_todo(client, "Second")
    resp = await client.put(f"/todos/{todo_id}", json={"title": "First"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


async def test_put_not_found(client: AsyncClient) -> None:
    """Non-existent id returns 404."""
    resp = await client.put("/todos/9999", json={"title": "Test"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_put_non_integer_id(client: AsyncClient) -> None:
    """Non-integer id returns 422."""
    resp = await client.put("/todos/abc", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_put_trims_title(client: AsyncClient) -> None:
    """Title is trimmed on update."""
    todo_id = await _create_todo(client)
    resp = await client.put(f"/todos/{todo_id}", json={"title": "  Buy eggs  "})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Buy eggs"


async def test_put_unknown_fields_ignored(client: AsyncClient) -> None:
    """Unknown fields are silently ignored."""
    todo_id = await _create_todo(client)
    resp = await client.put(
        f"/todos/{todo_id}", json={"title": "Buy eggs", "priority": "high"}
    )
    assert resp.status_code == 200
    assert "priority" not in resp.json()
