"""Tests for POST /todos/{id}/complete and /incomplete (Task 7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def _create_todo(client: AsyncClient, title: str = "Buy milk") -> int:
    resp = await client.post("/todos", json={"title": title})
    return resp.json()["id"]


async def test_complete_sets_completed_true(client: AsyncClient) -> None:
    """POST /todos/{id}/complete sets completed to true and returns full todo."""
    todo_id = await _create_todo(client)
    resp = await client.post(f"/todos/{todo_id}/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is True
    assert data["id"] == todo_id
    assert data["title"] == "Buy milk"


async def test_complete_idempotent(client: AsyncClient) -> None:
    """POST /todos/{id}/complete on already-complete todo succeeds."""
    todo_id = await _create_todo(client)
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.post(f"/todos/{todo_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["completed"] is True


async def test_incomplete_sets_completed_false(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete sets completed to false and returns full todo."""
    todo_id = await _create_todo(client)
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.post(f"/todos/{todo_id}/incomplete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is False
    assert data["id"] == todo_id
    assert data["title"] == "Buy milk"


async def test_incomplete_idempotent(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete on already-incomplete todo succeeds."""
    todo_id = await _create_todo(client)
    resp = await client.post(f"/todos/{todo_id}/incomplete")
    assert resp.status_code == 200
    assert resp.json()["completed"] is False


async def test_complete_not_found(client: AsyncClient) -> None:
    """POST /todos/{id}/complete with non-existent id returns 404."""
    resp = await client.post("/todos/9999/complete")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_incomplete_not_found(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete with non-existent id returns 404."""
    resp = await client.post("/todos/9999/incomplete")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


async def test_complete_non_integer_id(client: AsyncClient) -> None:
    """POST /todos/{id}/complete with non-integer id returns 422."""
    resp = await client.post("/todos/abc/complete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_incomplete_non_integer_id(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete with non-integer id returns 422."""
    resp = await client.post("/todos/abc/incomplete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


async def test_complete_with_body_succeeds(client: AsyncClient) -> None:
    """POST /todos/{id}/complete tolerates a request body without error."""
    todo_id = await _create_todo(client)
    resp = await client.post(f"/todos/{todo_id}/complete", json={"title": "ignored"})
    assert resp.status_code == 200
    assert resp.json()["completed"] is True
    assert resp.json()["title"] == "Buy milk"


async def test_incomplete_with_body_succeeds(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete tolerates a request body without error."""
    todo_id = await _create_todo(client)
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.post(f"/todos/{todo_id}/incomplete", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["completed"] is False
    assert resp.json()["title"] == "Buy milk"
