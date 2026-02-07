"""Tests for error handling consistency (Task 10)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_error_responses_use_detail_format(client: AsyncClient) -> None:
    """All error responses use {"detail": "..."} format."""
    # 422
    resp = await client.post("/todos", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)

    # 404
    resp = await client.get("/todos/9999")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


async def test_single_error_per_request(client: AsyncClient) -> None:
    """Only one error returned per request (not array format)."""
    resp = await client.post("/todos", json={})
    data = resp.json()
    assert isinstance(data["detail"], str)
    assert not isinstance(data.get("detail"), list)


async def test_validation_error_422(client: AsyncClient) -> None:
    """Validation errors return 422."""
    resp = await client.post("/todos", json={"title": ""})
    assert resp.status_code == 422


async def test_uniqueness_violation_409(client: AsyncClient) -> None:
    """Uniqueness violations return 409."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.post("/todos", json={"title": "Test"})
    assert resp.status_code == 409


async def test_missing_resource_404(client: AsyncClient) -> None:
    """Missing resources return 404."""
    resp = await client.get("/todos/9999")
    assert resp.status_code == 404


async def test_type_mismatch_title_integer(client: AsyncClient) -> None:
    """Type mismatch on title (e.g., title: 123) returns 422."""
    resp = await client.post("/todos", json={"title": 123})
    assert resp.status_code == 422
    assert "detail" in resp.json()


async def test_type_mismatch_completed_string(client: AsyncClient) -> None:
    """Type mismatch on completed (e.g., completed: 'yes') returns 422."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.get("/todos")
    todo_id = resp.json()[0]["id"]
    resp = await client.put(
        f"/todos/{todo_id}", json={"title": "Test", "completed": "yes"}
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


async def test_validation_order_missing_before_blank(client: AsyncClient) -> None:
    """Missing title takes priority over blank (validation order)."""
    resp = await client.post("/todos", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


async def test_validation_order_blank_before_uniqueness(client: AsyncClient) -> None:
    """Blank title takes priority over uniqueness check (validation order)."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.post("/todos", json={"title": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


async def test_validation_order_length_before_uniqueness(client: AsyncClient) -> None:
    """Length exceeded takes priority over uniqueness check (validation order)."""
    long_title = "x" * 501
    await client.post("/todos", json={"title": long_title})  # may or may not succeed
    resp = await client.post("/todos", json={"title": long_title})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"
