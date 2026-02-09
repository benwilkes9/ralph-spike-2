"""Tests for POST /todos endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_valid_todo(client: AsyncClient) -> None:
    """Valid POST with {"title": "Buy milk"} returns 201 with correct shape."""
    response = await client.post("/todos", json={"title": "Buy milk"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy milk"
    assert data["completed"] is False
    assert isinstance(data["id"], int)
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_create_todo_id_is_auto_generated(client: AsyncClient) -> None:
    """Returned id is an auto-generated positive integer."""
    r1 = await client.post("/todos", json={"title": "First"})
    r2 = await client.post("/todos", json={"title": "Second"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] > 0
    assert r2.json()["id"] > r1.json()["id"]


@pytest.mark.asyncio
async def test_create_todo_completed_always_false(client: AsyncClient) -> None:
    """completed is always false regardless of whether completed: true is sent."""
    response = await client.post(
        "/todos", json={"title": "Buy milk", "completed": True}
    )
    assert response.status_code == 201
    assert response.json()["completed"] is False


@pytest.mark.asyncio
async def test_create_todo_title_trimmed(client: AsyncClient) -> None:
    """POST with title "  Buy milk  " stores and returns "Buy milk" (trimmed)."""
    response = await client.post("/todos", json={"title": "  Buy milk  "})
    assert response.status_code == 201
    assert response.json()["title"] == "Buy milk"


@pytest.mark.asyncio
async def test_create_duplicate_case_insensitive(client: AsyncClient) -> None:
    """POST with same title different case returns 409."""
    r1 = await client.post("/todos", json={"title": "Buy milk"})
    assert r1.status_code == 201
    r2 = await client.post("/todos", json={"title": "buy milk"})
    assert r2.status_code == 409
    assert r2.json() == {"detail": "A todo with this title already exists"}


@pytest.mark.asyncio
async def test_create_duplicate_exact(client: AsyncClient) -> None:
    """POST with exact same title returns 409."""
    r1 = await client.post("/todos", json={"title": "Buy milk"})
    assert r1.status_code == 201
    r2 = await client.post("/todos", json={"title": "Buy milk"})
    assert r2.status_code == 409
    assert r2.json() == {"detail": "A todo with this title already exists"}


@pytest.mark.asyncio
async def test_create_missing_title(client: AsyncClient) -> None:
    """POST with {} (missing title) returns 422 "title is required"."""
    response = await client.post("/todos", json={})
    assert response.status_code == 422
    assert response.json() == {"detail": "title is required"}


@pytest.mark.asyncio
async def test_create_empty_title(client: AsyncClient) -> None:
    """POST with empty title returns 422 "title must not be blank"."""
    response = await client.post("/todos", json={"title": ""})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must not be blank"}


@pytest.mark.asyncio
async def test_create_whitespace_title(client: AsyncClient) -> None:
    """POST with whitespace-only title returns 422 "title must not be blank"."""
    response = await client.post("/todos", json={"title": "   "})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must not be blank"}


@pytest.mark.asyncio
async def test_create_title_too_long(client: AsyncClient) -> None:
    """POST with title > 500 chars returns 422."""
    response = await client.post("/todos", json={"title": "a" * 501})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must be 500 characters or fewer"}


@pytest.mark.asyncio
async def test_create_title_at_boundary(client: AsyncClient) -> None:
    """POST with title of exactly 500 chars succeeds."""
    response = await client.post("/todos", json={"title": "a" * 500})
    assert response.status_code == 201
    assert len(response.json()["title"]) == 500


@pytest.mark.asyncio
async def test_create_title_wrong_type(client: AsyncClient) -> None:
    """POST with title as integer returns 422 (type error)."""
    response = await client.post("/todos", json={"title": 123})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_create_unknown_fields_ignored(client: AsyncClient) -> None:
    """POST with unknown fields succeeds (unknown fields silently ignored)."""
    response = await client.post("/todos", json={"title": "Buy milk", "foo": "bar"})
    assert response.status_code == 201
    assert response.json()["title"] == "Buy milk"


@pytest.mark.asyncio
async def test_create_completed_true_ignored(client: AsyncClient) -> None:
    """POST with completed: true returns 201 with completed: false."""
    response = await client.post(
        "/todos", json={"title": "Buy milk", "completed": True}
    )
    assert response.status_code == 201
    assert response.json()["completed"] is False


@pytest.mark.asyncio
async def test_create_completed_invalid_type_ignored(client: AsyncClient) -> None:
    """POST with completed: "invalid" succeeds.

    completed is silently ignored on create.
    """
    response = await client.post(
        "/todos", json={"title": "Buy groceries", "completed": "invalid"}
    )
    assert response.status_code == 201
    assert response.json()["completed"] is False


@pytest.mark.asyncio
async def test_create_only_unknown_fields(client: AsyncClient) -> None:
    """POST with only unknown fields (no title) returns 422 "title is required"."""
    response = await client.post("/todos", json={"foo": "bar"})
    assert response.status_code == 422
    assert response.json() == {"detail": "title is required"}


@pytest.mark.asyncio
async def test_create_blank_title_over_duplicate(client: AsyncClient) -> None:
    """Blank title takes priority over uniqueness per validation order."""
    await client.post("/todos", json={"title": ""})
    # Even if a duplicate existed, blank should come first
    response = await client.post("/todos", json={"title": ""})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must not be blank"}


@pytest.mark.asyncio
async def test_create_long_title_over_duplicate(client: AsyncClient) -> None:
    """Length error takes priority over uniqueness per validation order."""
    long_title = "a" * 501
    # Even if a duplicate existed, length should come first
    response = await client.post("/todos", json={"title": long_title})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must be 500 characters or fewer"}
