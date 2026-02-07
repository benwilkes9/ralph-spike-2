"""Tests for PATCH /todos/{id} (Task 6)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def _create_todo(
    client: AsyncClient, title: str = "Buy milk", completed: bool = False
) -> int:
    resp = await client.post("/todos", json={"title": title})
    todo_id: int = resp.json()["id"]
    if completed:
        await client.post(f"/todos/{todo_id}/complete")
    return todo_id


async def test_patch_updates_only_provided_fields(client: AsyncClient) -> None:
    """PATCH updates only provided fields."""
    todo_id = await _create_todo(client)
    resp = await client.patch(
        f"/todos/{todo_id}", json={"title": "Buy eggs", "completed": True}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Buy eggs"
    assert data["completed"] is True


async def test_patch_title_only_completed_unchanged(client: AsyncClient) -> None:
    """PATCH title only — completed unchanged."""
    todo_id = await _create_todo(client, completed=True)
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "Buy eggs"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Buy eggs"
    assert resp.json()["completed"] is True


async def test_patch_completed_only_title_unchanged(client: AsyncClient) -> None:
    """PATCH completed only — title unchanged."""
    todo_id = await _create_todo(client)
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Buy milk"
    assert resp.json()["completed"] is True


async def test_patch_no_fields(client: AsyncClient) -> None:
    """PATCH with no fields returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.patch(f"/todos/{todo_id}", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "At least one field must be provided"


async def test_patch_only_unknown_fields(client: AsyncClient) -> None:
    """PATCH with only unknown fields returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.patch(f"/todos/{todo_id}", json={"priority": "high"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "At least one field must be provided"


async def test_patch_blank_title(client: AsyncClient) -> None:
    """Blank title returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.patch(f"/todos/{todo_id}", json={"title": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


async def test_patch_whitespace_title(client: AsyncClient) -> None:
    """Whitespace-only title returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


async def test_patch_title_too_long(client: AsyncClient) -> None:
    """Title > 500 chars returns 422."""
    todo_id = await _create_todo(client)
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "x" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


async def test_patch_duplicate_title(client: AsyncClient) -> None:
    """Duplicate title returns 409."""
    await _create_todo(client, "First")
    todo_id = await _create_todo(client, "Second")
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "First"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


async def test_patch_not_found(client: AsyncClient) -> None:
    """Non-existent id returns 404."""
    resp = await client.patch("/todos/9999", json={"title": "Test"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_patch_non_integer_id(client: AsyncClient) -> None:
    """Non-integer id returns 422."""
    resp = await client.patch("/todos/abc", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_patch_trims_title(client: AsyncClient) -> None:
    """Title is trimmed on PATCH update."""
    todo_id = await _create_todo(client)
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "  Buy eggs  "})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Buy eggs"


async def test_patch_trimmed_duplicate(client: AsyncClient) -> None:
    """Whitespace-padded title duplicate after trimming returns 409."""
    await _create_todo(client, "First")
    todo_id = await _create_todo(client, "Second")
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "  First  "})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


async def test_patch_own_title_succeeds(client: AsyncClient) -> None:
    """PATCH with same title as current todo succeeds (self-exclusion)."""
    todo_id = await _create_todo(client, "Buy milk")
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "Buy milk"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Buy milk"


async def test_patch_own_title_different_case_succeeds(client: AsyncClient) -> None:
    """PATCH with own title in different case succeeds (self-exclusion)."""
    todo_id = await _create_todo(client, "Buy milk")
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "BUY MILK"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "BUY MILK"


async def test_patch_unknown_with_valid_fields(client: AsyncClient) -> None:
    """PATCH with unknown fields alongside valid fields succeeds."""
    todo_id = await _create_todo(client)
    resp = await client.patch(
        f"/todos/{todo_id}", json={"title": "Buy eggs", "junk": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Buy eggs"
    assert "junk" not in resp.json()
