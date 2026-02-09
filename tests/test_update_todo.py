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
    assert resp.json()["detail"] == "A todo with this title already exists"


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
    assert resp.json()["detail"] == "Todo not found"


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
    assert resp.json()["detail"] == "Todo not found"


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
    assert resp.json()["detail"] == "Todo not found"


@pytest.mark.asyncio
async def test_incomplete_not_found(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete returns 404 for non-existent id."""
    resp = await client.post("/todos/9999/incomplete")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


@pytest.mark.asyncio
async def test_complete_non_integer_id(client: AsyncClient) -> None:
    """POST /todos/{id}/complete returns 422 for non-integer id."""
    resp = await client.post("/todos/abc/complete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


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


# --- Float id validation across endpoints ---


@pytest.mark.asyncio
async def test_get_float_id(client: AsyncClient) -> None:
    """GET /todos/1.5 returns 422."""
    resp = await client.get("/todos/1.5")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_put_float_id(client: AsyncClient) -> None:
    """PUT /todos/1.5 returns 422."""
    resp = await client.put("/todos/1.5", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_float_id(client: AsyncClient) -> None:
    """DELETE /todos/1.5 returns 422."""
    resp = await client.delete("/todos/1.5")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_complete_float_id(client: AsyncClient) -> None:
    """POST /todos/1.5/complete returns 422."""
    resp = await client.post("/todos/1.5/complete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_incomplete_float_id(client: AsyncClient) -> None:
    """POST /todos/1.5/incomplete returns 422."""
    resp = await client.post("/todos/1.5/incomplete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- Missing edge cases: non-integer and negative IDs ---


@pytest.mark.asyncio
async def test_incomplete_non_integer_id(client: AsyncClient) -> None:
    """POST /todos/abc/incomplete returns 422."""
    resp = await client.post("/todos/abc/incomplete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_complete_negative_id(client: AsyncClient) -> None:
    """POST /todos/-1/complete returns 422."""
    resp = await client.post("/todos/-1/complete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_incomplete_negative_id(client: AsyncClient) -> None:
    """POST /todos/-1/incomplete returns 422."""
    resp = await client.post("/todos/-1/incomplete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- PUT/PATCH title exactly 500 chars accepted ---


@pytest.mark.asyncio
async def test_put_title_exactly_500(client: AsyncClient) -> None:
    """PUT with title of exactly 500 characters is accepted."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "a" * 500})
    assert resp.status_code == 200
    assert len(resp.json()["title"]) == 500


@pytest.mark.asyncio
async def test_patch_title_exactly_500(client: AsyncClient) -> None:
    """PATCH with title of exactly 500 characters is accepted."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "b" * 500})
    assert resp.status_code == 200
    assert len(resp.json()["title"]) == 500


# --- PUT validation order: missing title before bad completed ---


@pytest.mark.asyncio
async def test_put_missing_title_before_bad_completed(
    client: AsyncClient,
) -> None:
    """PUT: missing title (priority 1) before bad completed type (priority 2)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"completed": "yes"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


# --- Response shape for all update endpoints ---


@pytest.mark.asyncio
async def test_put_response_shape(client: AsyncClient) -> None:
    """PUT response contains exactly id, title, completed."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "Updated"})
    assert set(resp.json().keys()) == {"id", "title", "completed"}


@pytest.mark.asyncio
async def test_patch_response_shape(client: AsyncClient) -> None:
    """PATCH response contains exactly id, title, completed."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "Updated"})
    assert set(resp.json().keys()) == {"id", "title", "completed"}


@pytest.mark.asyncio
async def test_complete_response_shape(client: AsyncClient) -> None:
    """POST /todos/{id}/complete response has exactly {id, title, completed}."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.post(f"/todos/{todo_id}/complete")
    assert set(resp.json().keys()) == {"id", "title", "completed"}


@pytest.mark.asyncio
async def test_incomplete_response_shape(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete response has exactly {id, title, completed}."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.post(f"/todos/{todo_id}/incomplete")
    assert set(resp.json().keys()) == {"id", "title", "completed"}


# --- PUT/PATCH title uniqueness after trim ---


@pytest.mark.asyncio
async def test_put_trim_then_uniqueness(client: AsyncClient) -> None:
    """PUT: title duplicate after trimming returns 409."""
    await client.post("/todos", json={"title": "Existing"})
    r = await client.post("/todos", json={"title": "Other"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "  Existing  "})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


@pytest.mark.asyncio
async def test_patch_trim_then_uniqueness(client: AsyncClient) -> None:
    """PATCH: title duplicate after trimming returns 409."""
    await client.post("/todos", json={"title": "Existing"})
    r = await client.post("/todos", json={"title": "Other"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "  Existing  "})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "A todo with this title already exists"


# --- PUT omitting completed resets to false, verified by GET ---


@pytest.mark.asyncio
async def test_put_reset_completed_persists(client: AsyncClient) -> None:
    """PUT omitting completed resets to false; verified via GET."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    await client.put(f"/todos/{todo_id}", json={"title": "Test"})
    resp = await client.get(f"/todos/{todo_id}")
    assert resp.json()["completed"] is False


# --- PUT/PATCH empty string title (not just whitespace) ---


@pytest.mark.asyncio
async def test_put_empty_string_title(client: AsyncClient) -> None:
    """PUT with title: '' returns 422 title must not be blank."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_patch_empty_string_title(client: AsyncClient) -> None:
    """PATCH with title: '' returns 422 title must not be blank."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


# --- PUT with explicit completed: false ---


@pytest.mark.asyncio
async def test_put_explicit_completed_false(client: AsyncClient) -> None:
    """PUT with explicit completed: false sets completed to false."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Updated", "completed": False},
    )
    assert resp.status_code == 200
    assert resp.json()["completed"] is False


# --- POST /todos with id field is ignored ---


@pytest.mark.asyncio
async def test_create_id_field_ignored(client: AsyncClient) -> None:
    """POST /todos with id: 999 in body ignores it; auto-generates id."""
    resp = await client.post("/todos", json={"title": "Test ID", "id": 999})
    assert resp.status_code == 201
    assert isinstance(resp.json()["id"], int)
    # Verify by checking the todo exists at the returned id
    todo_id = resp.json()["id"]
    get_resp = await client.get(f"/todos/{todo_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Test ID"


# --- PUT/PATCH with id field in body (should be ignored) ---


@pytest.mark.asyncio
async def test_put_id_field_in_body_ignored(client: AsyncClient) -> None:
    """PUT with id in body ignores it; uses path id."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Updated", "id": 999},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id
    assert resp.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_patch_id_field_in_body_ignored(client: AsyncClient) -> None:
    """PATCH with id in body ignores it; uses path id."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "Updated", "id": 999},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id
    assert resp.json()["title"] == "Updated"


# --- PATCH cross-field: completed:null with title also provided ---


@pytest.mark.asyncio
async def test_patch_completed_null_with_title(client: AsyncClient) -> None:
    """PATCH: completed:null type error (priority 2) even with valid title."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "Valid", "completed": None},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


# --- PUT/PATCH with list/object title types ---


@pytest.mark.asyncio
async def test_put_title_list(client: AsyncClient) -> None:
    """PUT with title: [] returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": []})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_patch_title_list(client: AsyncClient) -> None:
    """PATCH with title: [] returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": []})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- Case-insensitive self-exclusion on title uniqueness ---


@pytest.mark.asyncio
async def test_put_same_title_different_case_self(
    client: AsyncClient,
) -> None:
    """PUT: changing title to case-different version of own title succeeds."""
    r = await client.post("/todos", json={"title": "My Task"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "MY TASK"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "MY TASK"


@pytest.mark.asyncio
async def test_patch_same_title_different_case_self(
    client: AsyncClient,
) -> None:
    """PATCH: changing title to case-different version of own title succeeds."""
    r = await client.post("/todos", json={"title": "My Task"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "MY TASK"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "MY TASK"


# --- Trim-before-length on PUT/PATCH ---


@pytest.mark.asyncio
async def test_put_title_500_after_trim(client: AsyncClient) -> None:
    """PUT: title >500 before trim but exactly 500 after trim is accepted."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    title_500 = "a" * 500
    resp = await client.put(f"/todos/{todo_id}", json={"title": f"  {title_500}  "})
    assert resp.status_code == 200
    assert len(resp.json()["title"]) == 500


@pytest.mark.asyncio
async def test_patch_title_500_after_trim(client: AsyncClient) -> None:
    """PATCH: title >500 before trim but exactly 500 after trim is accepted."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    title_500 = "b" * 500
    resp = await client.patch(f"/todos/{todo_id}", json={"title": f"  {title_500}  "})
    assert resp.status_code == 200
    assert len(resp.json()["title"]) == 500


# --- PATCH idempotent completed=false ---


@pytest.mark.asyncio
async def test_patch_completed_false_on_already_false(
    client: AsyncClient,
) -> None:
    """PATCH: setting completed=false on already-false todo succeeds."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": False})
    assert resp.status_code == 200
    assert resp.json()["completed"] is False


# --- POST with completed: false ignored ---


@pytest.mark.asyncio
async def test_create_todo_completed_false_ignored(
    client: AsyncClient,
) -> None:
    """POST with completed: false is ignored (default is false anyway)."""
    resp = await client.post("/todos", json={"title": "Test CF", "completed": False})
    assert resp.status_code == 201
    assert resp.json()["completed"] is False


# --- PATCH valid title + invalid completed ---


@pytest.mark.asyncio
async def test_patch_valid_title_invalid_completed_string(
    client: AsyncClient,
) -> None:
    """PATCH: valid title + completed:'yes' returns completed type error."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "Valid Title", "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_patch_valid_title_invalid_completed_int(
    client: AsyncClient,
) -> None:
    """PATCH: valid title + completed:1 returns completed type error."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "Valid Title", "completed": 1},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


# --- PATCH invalid title + valid completed ---


@pytest.mark.asyncio
async def test_patch_invalid_title_valid_completed(
    client: AsyncClient,
) -> None:
    """PATCH: title:123 + completed:true returns title type error."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": 123, "completed": True},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- PUT title:null + valid completed ---


@pytest.mark.asyncio
async def test_put_title_null_valid_completed(
    client: AsyncClient,
) -> None:
    """PUT: title:null + completed:true returns 'title is required'."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": None, "completed": True},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


# --- PATCH completed-only skips uniqueness check ---


@pytest.mark.asyncio
async def test_patch_completed_only_no_uniqueness_check(
    client: AsyncClient,
) -> None:
    """PATCH: completing a todo skips uniqueness even if title matches another."""
    await client.post("/todos", json={"title": "Hello"})
    r = await client.post("/todos", json={"title": "World"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["completed"] is True
    assert resp.json()["title"] == "World"


# --- Create with completed: null ignored ---


@pytest.mark.asyncio
async def test_create_completed_null_ignored(
    client: AsyncClient,
) -> None:
    """POST: completed:null is ignored on create, defaults to false."""
    resp = await client.post(
        "/todos", json={"title": "Null Completed", "completed": None}
    )
    assert resp.status_code == 201
    assert resp.json()["completed"] is False


# --- PATCH empty string title + valid completed ---


@pytest.mark.asyncio
async def test_patch_empty_title_valid_completed(
    client: AsyncClient,
) -> None:
    """PATCH: empty string title + valid completed returns blank error."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "", "completed": True},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


# --- Incomplete endpoint ignores request body ---


@pytest.mark.asyncio
async def test_incomplete_ignores_body(client: AsyncClient) -> None:
    """POST /todos/{id}/incomplete ignores any request body."""
    r = await client.post("/todos", json={"title": "Body Test"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.post(
        f"/todos/{todo_id}/incomplete",
        json={"foo": "bar", "title": "Ignored"},
    )
    assert resp.status_code == 200
    assert resp.json()["completed"] is False
    assert resp.json()["title"] == "Body Test"


# --- PATCH completed true -> false ---


@pytest.mark.asyncio
async def test_patch_completed_true_to_false(
    client: AsyncClient,
) -> None:
    """PATCH: change completed from true to false."""
    r = await client.post("/todos", json={"title": "Toggle"})
    todo_id = r.json()["id"]
    await client.post(f"/todos/{todo_id}/complete")
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": False})
    assert resp.status_code == 200
    assert resp.json()["completed"] is False
    # Verify persisted
    get_resp = await client.get(f"/todos/{todo_id}")
    assert get_resp.json()["completed"] is False


# --- PUT/PATCH response id matches path ---


@pytest.mark.asyncio
async def test_put_response_id_matches_path(
    client: AsyncClient,
) -> None:
    """PUT response id equals the path parameter id."""
    r = await client.post("/todos", json={"title": "Match ID"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id


@pytest.mark.asyncio
async def test_patch_response_id_matches_path(
    client: AsyncClient,
) -> None:
    """PATCH response id equals the path parameter id."""
    r = await client.post("/todos", json={"title": "Match ID 2"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "Patched"})
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id
