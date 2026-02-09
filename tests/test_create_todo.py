"""Tests for POST /todos endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_todo_success(client: AsyncClient) -> None:
    """A valid POST with a title creates a todo and returns 201."""
    resp = await client.post("/todos", json={"title": "Buy groceries"})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Buy groceries"
    assert data["completed"] is False


@pytest.mark.asyncio
async def test_create_todo_id_is_unique_integer(client: AsyncClient) -> None:
    """The returned id is a unique auto-generated integer."""
    r1 = await client.post("/todos", json={"title": "Todo 1"})
    r2 = await client.post("/todos", json={"title": "Todo 2"})
    assert isinstance(r1.json()["id"], int)
    assert isinstance(r2.json()["id"], int)
    assert r1.json()["id"] != r2.json()["id"]


@pytest.mark.asyncio
async def test_create_todo_completed_always_false(client: AsyncClient) -> None:
    """The returned completed is always false."""
    resp = await client.post("/todos", json={"title": "Test"})
    assert resp.json()["completed"] is False


@pytest.mark.asyncio
async def test_create_todo_completed_true_ignored(client: AsyncClient) -> None:
    """Sending completed: true is ignored; the created todo has completed: false."""
    resp = await client.post("/todos", json={"title": "Test", "completed": True})
    assert resp.status_code == 201
    assert resp.json()["completed"] is False


@pytest.mark.asyncio
async def test_create_todo_whitespace_trimmed(client: AsyncClient) -> None:
    """Leading and trailing whitespace in title is trimmed."""
    resp = await client.post("/todos", json={"title": "  Buy milk  "})
    assert resp.status_code == 201
    assert resp.json()["title"] == "Buy milk"


@pytest.mark.asyncio
async def test_create_todo_missing_title(client: AsyncClient) -> None:
    """A request with missing title field returns 422."""
    resp = await client.post("/todos", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


@pytest.mark.asyncio
async def test_create_todo_empty_title(client: AsyncClient) -> None:
    """A request with an empty string title returns 422."""
    resp = await client.post("/todos", json={"title": ""})
    assert resp.status_code == 422
    assert "blank" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_todo_whitespace_only_title(client: AsyncClient) -> None:
    """A request with a whitespace-only title returns 422."""
    resp = await client.post("/todos", json={"title": "   "})
    assert resp.status_code == 422
    assert "blank" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_todo_title_too_long(client: AsyncClient) -> None:
    """A request with title exceeding 500 characters returns 422."""
    resp = await client.post("/todos", json={"title": "a" * 501})
    assert resp.status_code == 422
    assert "500" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_todo_duplicate_title(client: AsyncClient) -> None:
    """Creating a todo with a duplicate title returns 409."""
    await client.post("/todos", json={"title": "Buy milk"})
    resp = await client.post("/todos", json={"title": "Buy milk"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_todo_duplicate_title_case_insensitive(
    client: AsyncClient,
) -> None:
    """Titles 'Buy milk' and 'buy milk' are treated as duplicates."""
    await client.post("/todos", json={"title": "Buy milk"})
    resp = await client.post("/todos", json={"title": "buy milk"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_todo_title_exactly_500(client: AsyncClient) -> None:
    """A title of exactly 500 characters is accepted."""
    resp = await client.post("/todos", json={"title": "a" * 500})
    assert resp.status_code == 201
    assert len(resp.json()["title"]) == 500


@pytest.mark.asyncio
async def test_create_todo_unknown_fields_ignored(client: AsyncClient) -> None:
    """Unknown fields in the request body are silently ignored."""
    resp = await client.post(
        "/todos", json={"title": "Test", "foo": "bar", "priority": 1}
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Test"


@pytest.mark.asyncio
async def test_create_todo_title_non_string(client: AsyncClient) -> None:
    """Sending title as a non-string type returns 422."""
    resp = await client.post("/todos", json={"title": 123})
    assert resp.status_code == 422
