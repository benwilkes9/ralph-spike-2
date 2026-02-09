"""Tests for PUT, PATCH, POST complete/incomplete endpoints."""

import pytest
from httpx import AsyncClient

# --- PUT /todos/{id} ---


@pytest.mark.asyncio
async def test_put_valid_title(client: AsyncClient) -> None:
    """PUT with valid title updates the todo and returns 200."""
    r = await client.post("/todos", json={"title": "Original"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_put_replaces_both_fields(client: AsyncClient) -> None:
    """PUT replaces both title and completed fields."""
    r = await client.post("/todos", json={"title": "Original"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "New", "completed": True},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
    assert resp.json()["completed"] is True


@pytest.mark.asyncio
async def test_put_title_only_resets_completed(client: AsyncClient) -> None:
    """PUT with title only resets completed to false."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.put(f"/todos/{todo_id}", json={"title": "Test"})
    assert resp.status_code == 200
    assert resp.json()["completed"] is False


@pytest.mark.asyncio
async def test_put_with_completed_true(client: AsyncClient) -> None:
    """PUT with title and completed: true sets both."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Updated", "completed": True},
    )
    assert resp.json()["title"] == "Updated"
    assert resp.json()["completed"] is True


@pytest.mark.asyncio
async def test_put_missing_title(client: AsyncClient) -> None:
    """PUT with missing title returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"completed": True})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


@pytest.mark.asyncio
async def test_put_blank_title(client: AsyncClient) -> None:
    """PUT with blank title returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_put_title_too_long(client: AsyncClient) -> None:
    """PUT with title exceeding 500 characters returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "a" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


@pytest.mark.asyncio
async def test_put_duplicate_title(client: AsyncClient) -> None:
    """PUT with a duplicate title returns 409."""
    await client.post("/todos", json={"title": "Existing"})
    r = await client.post("/todos", json={"title": "Other"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "existing"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_put_same_title_self(client: AsyncClient) -> None:
    """PUT updating a todo's title to its own current title succeeds."""
    r = await client.post("/todos", json={"title": "Same"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "Same"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_put_not_found(client: AsyncClient) -> None:
    """PUT with a non-existent id returns 404."""
    resp = await client.put("/todos/9999", json={"title": "Test"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_non_integer_id(client: AsyncClient) -> None:
    """PUT with a non-integer id returns 422."""
    resp = await client.put("/todos/abc", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_put_trims_whitespace(client: AsyncClient) -> None:
    """Title whitespace is trimmed on PUT."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "  Updated  "})
    assert resp.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_put_ignores_unknown_fields(client: AsyncClient) -> None:
    """Unknown fields in PUT body are silently ignored."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Updated", "foo": "bar"},
    )
    assert resp.status_code == 200


# --- PATCH /todos/{id} ---


@pytest.mark.asyncio
async def test_patch_title_only(client: AsyncClient) -> None:
    """PATCH with only title updates the title, leaves completed unchanged."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
    assert resp.json()["completed"] is True


@pytest.mark.asyncio
async def test_patch_completed_only(client: AsyncClient) -> None:
    """PATCH with only completed updates status, leaves title unchanged."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["completed"] is True
    assert resp.json()["title"] == "Test"


@pytest.mark.asyncio
async def test_patch_both_fields(client: AsyncClient) -> None:
    """PATCH with both title and completed updates both."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "Updated", "completed": True},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"
    assert resp.json()["completed"] is True


@pytest.mark.asyncio
async def test_patch_empty_body(client: AsyncClient) -> None:
    """PATCH with empty body returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "At least one field must be provided"


@pytest.mark.asyncio
async def test_patch_only_unknown_fields(client: AsyncClient) -> None:
    """PATCH with only unknown fields returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"foo": "bar"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "At least one field must be provided"


@pytest.mark.asyncio
async def test_patch_blank_title(client: AsyncClient) -> None:
    """PATCH with blank title returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_patch_title_too_long(client: AsyncClient) -> None:
    """PATCH with title exceeding 500 characters returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "a" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


@pytest.mark.asyncio
async def test_patch_duplicate_title(client: AsyncClient) -> None:
    """PATCH with a duplicate title returns 409."""
    await client.post("/todos", json={"title": "Existing"})
    r = await client.post("/todos", json={"title": "Other"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "existing"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


@pytest.mark.asyncio
async def test_patch_same_title_self(client: AsyncClient) -> None:
    """PATCH updating title to the same value succeeds."""
    r = await client.post("/todos", json={"title": "Same"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "Same"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_patch_not_found(client: AsyncClient) -> None:
    """PATCH with a non-existent id returns 404."""
    resp = await client.patch("/todos/9999", json={"title": "Test"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_non_integer_id(client: AsyncClient) -> None:
    """PATCH with a non-integer id returns 422."""
    resp = await client.patch("/todos/abc", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_patch_trims_whitespace(client: AsyncClient) -> None:
    """Title whitespace is trimmed on PATCH."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "  Updated  "})
    assert resp.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_patch_unknown_fields_alongside_known(
    client: AsyncClient,
) -> None:
    """Unknown fields alongside recognized fields are silently ignored."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "New", "unknown_field": "value"},
    )
    assert resp.status_code == 200


# --- POST /todos/{id}/complete and /incomplete ---


@pytest.mark.asyncio
async def test_complete_todo(client: AsyncClient) -> None:
    """POST /todos/{id}/complete sets completed to true and returns full todo."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.post(f"/todos/{todo_id}/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is True
    assert data["id"] == todo_id
    assert data["title"] == "Test"


@pytest.mark.asyncio
async def test_complete_already_completed(client: AsyncClient) -> None:
    """POST /todos/{id}/complete on already-completed is idempotent."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.post(f"/todos/{todo_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["completed"] is True


@pytest.mark.asyncio
async def test_incomplete_todo(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete sets completed to false and returns full todo."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.post(f"/todos/{todo_id}/incomplete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is False
    assert data["id"] == todo_id
    assert data["title"] == "Test"


@pytest.mark.asyncio
async def test_incomplete_already_incomplete(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete on already-incomplete is idempotent."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.post(f"/todos/{todo_id}/incomplete")
    assert resp.status_code == 200
    assert resp.json()["completed"] is False


@pytest.mark.asyncio
async def test_complete_not_found(client: AsyncClient) -> None:
    """POST /todos/{id}/complete returns 404 for non-existent id."""
    resp = await client.post("/todos/9999/complete")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_incomplete_not_found(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete returns 404 for non-existent id."""
    resp = await client.post("/todos/9999/incomplete")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_complete_non_integer_id(client: AsyncClient) -> None:
    """POST /todos/{id}/complete returns 422 for non-integer id."""
    resp = await client.post("/todos/abc/complete")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_incomplete_zero_id(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete returns 422 for zero id."""
    resp = await client.post("/todos/0/incomplete")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_complete_ignores_body(client: AsyncClient) -> None:
    """Complete/incomplete endpoints ignore any request body."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.post(
        f"/todos/{todo_id}/complete",
        json={"foo": "bar"},
    )
    assert resp.status_code == 200


# --- Additional edge cases ---


@pytest.mark.asyncio
async def test_patch_title_null(client: AsyncClient) -> None:
    """PATCH with title: null returns 422 (type error, not missing)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": None})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_patch_title_non_string(client: AsyncClient) -> None:
    """PATCH with title as a non-string type returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": 123})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_patch_completed_null(client: AsyncClient) -> None:
    """PATCH with completed: null returns 422 (type error)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": None})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_put_title_null(client: AsyncClient) -> None:
    """PUT with title: null returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": None})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


@pytest.mark.asyncio
async def test_put_title_non_string(client: AsyncClient) -> None:
    """PUT with title as a non-string type returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": 123})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_put_completed_string(client: AsyncClient) -> None:
    """PUT with completed: 'yes' returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Valid", "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_put_empty_body(client: AsyncClient) -> None:
    """PUT with empty body returns 422 with 'title is required'."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


@pytest.mark.asyncio
async def test_put_completed_integer_rejected(client: AsyncClient) -> None:
    """PUT with completed: 1 returns 422 (integers are not booleans)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Valid", "completed": 1},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_patch_completed_integer_rejected(client: AsyncClient) -> None:
    """PATCH with completed: 0 returns 422 (integers are not booleans)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": 0})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"
