"""Tests for POST /todos (Task 3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_create_todo_success(client: AsyncClient) -> None:
    """Valid POST creates todo and returns 201."""
    resp = await client.post("/todos", json={"title": "Buy milk"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Buy milk"
    assert data["completed"] is False
    assert isinstance(data["id"], int)


async def test_create_todo_id_is_auto_generated(client: AsyncClient) -> None:
    """Returned id is an auto-generated integer."""
    r1 = await client.post("/todos", json={"title": "First"})
    r2 = await client.post("/todos", json={"title": "Second"})
    assert r1.json()["id"] != r2.json()["id"]
    assert isinstance(r1.json()["id"], int)


async def test_create_todo_completed_always_false(client: AsyncClient) -> None:
    """Completed is always false on creation, even if sent in body."""
    resp = await client.post("/todos", json={"title": "Buy milk", "completed": True})
    assert resp.status_code == 201
    assert resp.json()["completed"] is False


async def test_create_todo_missing_title(client: AsyncClient) -> None:
    """Missing title returns 422."""
    resp = await client.post("/todos", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


async def test_create_todo_empty_title(client: AsyncClient) -> None:
    """Empty string title returns 422."""
    resp = await client.post("/todos", json={"title": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


async def test_create_todo_whitespace_only_title(client: AsyncClient) -> None:
    """Whitespace-only title returns 422."""
    resp = await client.post("/todos", json={"title": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


async def test_create_todo_title_too_long(client: AsyncClient) -> None:
    """Title > 500 chars returns 422."""
    resp = await client.post("/todos", json={"title": "x" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


async def test_create_todo_duplicate_title_case_insensitive(
    client: AsyncClient,
) -> None:
    """Duplicate title (case-insensitive) returns 409."""
    await client.post("/todos", json={"title": "Buy Milk"})
    resp = await client.post("/todos", json={"title": "buy milk"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


async def test_create_todo_trims_whitespace(client: AsyncClient) -> None:
    """Leading/trailing whitespace is trimmed in stored title."""
    resp = await client.post("/todos", json={"title": "  Buy milk  "})
    assert resp.status_code == 201
    assert resp.json()["title"] == "Buy milk"


async def test_create_todo_unknown_fields_ignored(client: AsyncClient) -> None:
    """Unknown fields in body are silently ignored."""
    resp = await client.post(
        "/todos", json={"title": "Buy milk", "priority": "high", "foo": 42}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "priority" not in data
    assert "foo" not in data


async def test_create_todo_trimmed_duplicate(client: AsyncClient) -> None:
    """Whitespace-padded title is duplicate of existing after trimming (409)."""
    await client.post("/todos", json={"title": "Buy milk"})
    resp = await client.post("/todos", json={"title": "  Buy milk  "})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"
