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
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_create_todo_whitespace_only_title(client: AsyncClient) -> None:
    """A request with a whitespace-only title returns 422."""
    resp = await client.post("/todos", json={"title": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_create_todo_title_too_long(client: AsyncClient) -> None:
    """A request with title exceeding 500 characters returns 422."""
    resp = await client.post("/todos", json={"title": "a" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


@pytest.mark.asyncio
async def test_create_todo_duplicate_title(client: AsyncClient) -> None:
    """Creating a todo with a duplicate title returns 409."""
    await client.post("/todos", json={"title": "Buy milk"})
    resp = await client.post("/todos", json={"title": "Buy milk"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


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
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_create_todo_duplicate_after_trim_and_case_fold(
    client: AsyncClient,
) -> None:
    """A title matching after trimming and case folding is a duplicate."""
    await client.post("/todos", json={"title": "Buy milk"})
    resp = await client.post("/todos", json={"title": "  Buy Milk  "})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


@pytest.mark.asyncio
async def test_create_todo_title_500_after_trim(client: AsyncClient) -> None:
    """Title over 500 chars before trim but exactly 500 after is OK."""
    title_500 = "a" * 500
    resp = await client.post("/todos", json={"title": f"  {title_500}  "})
    assert resp.status_code == 201
    assert len(resp.json()["title"]) == 500


# --- Unicode title tests ---


@pytest.mark.asyncio
async def test_create_todo_unicode_title(client: AsyncClient) -> None:
    """Unicode characters in title are accepted and preserved."""
    resp = await client.post("/todos", json={"title": "Acheter du lait"})
    assert resp.status_code == 201
    assert resp.json()["title"] == "Acheter du lait"


@pytest.mark.asyncio
async def test_create_todo_unicode_emoji_title(client: AsyncClient) -> None:
    """Emoji characters in title are accepted and preserved."""
    resp = await client.post("/todos", json={"title": "Buy groceries \U0001f6d2"})
    assert resp.status_code == 201
    assert resp.json()["title"] == "Buy groceries \U0001f6d2"


@pytest.mark.asyncio
async def test_create_todo_unicode_duplicate_case_insensitive(
    client: AsyncClient,
) -> None:
    """Unicode title uniqueness is case-insensitive."""
    await client.post("/todos", json={"title": "Caf\u00e9"})
    resp = await client.post("/todos", json={"title": "caf\u00e9"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"
