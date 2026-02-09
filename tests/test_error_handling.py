"""Tests for error handling and validation cross-cutting concerns."""

import pytest
from httpx import AsyncClient

# --- Consistent error format ---


@pytest.mark.asyncio
async def test_422_has_detail_string(client: AsyncClient) -> None:
    """Every 422 response body has a detail key with a string value."""
    resp = await client.post("/todos", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


@pytest.mark.asyncio
async def test_404_has_detail_string(client: AsyncClient) -> None:
    """Every 404 response body has a detail key with a string value."""
    resp = await client.get("/todos/9999")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


@pytest.mark.asyncio
async def test_409_has_detail_string(client: AsyncClient) -> None:
    """Every 409 response body has a detail key with a string value."""
    await client.post("/todos", json={"title": "Dup"})
    resp = await client.post("/todos", json={"title": "Dup"})
    assert resp.status_code == 409
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


@pytest.mark.asyncio
async def test_no_errors_array_in_response(client: AsyncClient) -> None:
    """No error response contains an errors array."""
    resp = await client.post("/todos", json={})
    data = resp.json()
    assert "errors" not in data


# --- Validation ordering ---


@pytest.mark.asyncio
async def test_missing_title_first(client: AsyncClient) -> None:
    """Missing title error takes precedence over other checks."""
    resp = await client.post("/todos", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


@pytest.mark.asyncio
async def test_type_error_before_blank(client: AsyncClient) -> None:
    """Non-string title returns type error before blank check."""
    resp = await client.post("/todos", json={"title": 123})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_blank_before_length(client: AsyncClient) -> None:
    """Whitespace-only title returns blank error before length check."""
    resp = await client.post("/todos", json={"title": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_length_before_uniqueness(client: AsyncClient) -> None:
    """Over-length title returns length error before uniqueness check."""
    await client.post("/todos", json={"title": "a" * 500})
    resp = await client.post("/todos", json={"title": "a" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


@pytest.mark.asyncio
async def test_single_error_per_request(client: AsyncClient) -> None:
    """Only one error is returned per request."""
    resp = await client.post("/todos", json={})
    data = resp.json()
    assert isinstance(data["detail"], str)


# --- Unknown field handling ---


@pytest.mark.asyncio
async def test_create_ignores_extra_fields(client: AsyncClient) -> None:
    """POST /todos with extra fields creates the todo."""
    resp = await client.post("/todos", json={"title": "Test", "priority": 1})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_put_ignores_extra_fields(client: AsyncClient) -> None:
    """PUT with extra fields updates normally."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "New", "extra": "field"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_patch_only_unknown_returns_422(client: AsyncClient) -> None:
    """PATCH with only unknown fields returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"unknown_field": "value"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "At least one field must be provided"


@pytest.mark.asyncio
async def test_patch_known_and_unknown_succeeds(client: AsyncClient) -> None:
    """PATCH with known and unknown fields succeeds."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "New", "unknown_field": "value"},
    )
    assert resp.status_code == 200


# --- Type mismatch handling ---


@pytest.mark.asyncio
async def test_create_title_integer(client: AsyncClient) -> None:
    """POST /todos with title: 123 returns 422."""
    resp = await client.post("/todos", json={"title": 123})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_create_title_null(client: AsyncClient) -> None:
    """POST /todos with title: null returns 422 with 'title is required'."""
    resp = await client.post("/todos", json={"title": None})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


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
async def test_patch_completed_string(client: AsyncClient) -> None:
    """PATCH with completed: 'yes' returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": "yes"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_get_non_integer_path(client: AsyncClient) -> None:
    """GET /todos/abc returns 422."""
    resp = await client.get("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_non_integer_path(client: AsyncClient) -> None:
    """DELETE /todos/abc returns 422."""
    resp = await client.delete("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- Path parameter validation ---


@pytest.mark.asyncio
async def test_get_zero_id(client: AsyncClient) -> None:
    """GET /todos/0 returns 422."""
    resp = await client.get("/todos/0")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_put_negative_id(client: AsyncClient) -> None:
    """PUT /todos/-1 returns 422."""
    resp = await client.put("/todos/-1", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_patch_float_id(client: AsyncClient) -> None:
    """PATCH /todos/1.5 returns 422."""
    resp = await client.patch("/todos/1.5", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_abc_id(client: AsyncClient) -> None:
    """DELETE /todos/abc returns 422."""
    resp = await client.delete("/todos/abc")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_complete_abc_id(client: AsyncClient) -> None:
    """POST /todos/abc/complete returns 422."""
    resp = await client.post("/todos/abc/complete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_incomplete_zero_id(client: AsyncClient) -> None:
    """POST /todos/0/incomplete returns 422."""
    resp = await client.post("/todos/0/incomplete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- Cross-field validation ordering ---


@pytest.mark.asyncio
async def test_put_completed_type_before_title_blank(
    client: AsyncClient,
) -> None:
    """PUT: completed type error (priority 2) before title blank (3)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "   ", "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_patch_completed_type_before_title_blank(
    client: AsyncClient,
) -> None:
    """PATCH: completed type error (priority 2) before title blank (3)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "   ", "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


# --- Invalid JSON body handling ---


@pytest.mark.asyncio
async def test_create_invalid_json_body(client: AsyncClient) -> None:
    """POST /todos with malformed JSON returns 422."""
    resp = await client.post(
        "/todos",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_create_non_object_json_body(client: AsyncClient) -> None:
    """POST /todos with JSON array body returns 422."""
    resp = await client.post(
        "/todos",
        content=b"[1,2,3]",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Request body must be a JSON object"


@pytest.mark.asyncio
async def test_put_invalid_json_body(client: AsyncClient) -> None:
    """PUT with malformed JSON returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_put_non_object_json_body(client: AsyncClient) -> None:
    """PUT with JSON string body returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        content=b'"hello"',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Request body must be a JSON object"


@pytest.mark.asyncio
async def test_patch_invalid_json_body(client: AsyncClient) -> None:
    """PATCH with malformed JSON returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        content=b"{bad}",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_patch_non_object_json_body(client: AsyncClient) -> None:
    """PATCH with JSON null body returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        content=b"null",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Request body must be a JSON object"


# --- Very large path IDs ---


@pytest.mark.asyncio
async def test_get_very_large_id(client: AsyncClient) -> None:
    """GET /todos/{id} with id exceeding SQLite range returns 422."""
    resp = await client.get("/todos/99999999999999999999")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_very_large_id(client: AsyncClient) -> None:
    """DELETE /todos/{id} with very large id returns 422."""
    resp = await client.delete("/todos/9223372036854775808")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- PUT completed:null returns 422 (consistent with PATCH) ---


@pytest.mark.asyncio
async def test_put_completed_null_returns_422(client: AsyncClient) -> None:
    """PUT with completed: null returns 422 (null is not boolean)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Test", "completed": None},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


# --- Response shape ---


@pytest.mark.asyncio
async def test_create_response_has_only_expected_keys(
    client: AsyncClient,
) -> None:
    """POST /todos response contains exactly id, title, completed."""
    resp = await client.post("/todos", json={"title": "Test"})
    assert set(resp.json().keys()) == {"id", "title", "completed"}


@pytest.mark.asyncio
async def test_get_response_has_only_expected_keys(
    client: AsyncClient,
) -> None:
    """GET /todos/{id} response contains exactly id, title, completed."""
    r = await client.post("/todos", json={"title": "Test"})
    resp = await client.get(f"/todos/{r.json()['id']}")
    assert set(resp.json().keys()) == {"id", "title", "completed"}


# --- Validation order: missing title before bad completed ---


@pytest.mark.asyncio
async def test_create_missing_title_before_bad_completed(
    client: AsyncClient,
) -> None:
    """POST missing title takes priority over bad completed type."""
    resp = await client.post("/todos", json={"completed": "yes"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


# --- Non-string title types beyond integer ---


@pytest.mark.asyncio
async def test_create_title_boolean(client: AsyncClient) -> None:
    """POST /todos with title: true returns 422."""
    resp = await client.post("/todos", json={"title": True})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_create_title_list(client: AsyncClient) -> None:
    """POST /todos with title: [] returns 422."""
    resp = await client.post("/todos", json={"title": []})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_create_title_object(client: AsyncClient) -> None:
    """POST /todos with title: {} returns 422."""
    resp = await client.post("/todos", json={"title": {}})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_put_title_boolean(client: AsyncClient) -> None:
    """PUT with title: true returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": True})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_patch_title_boolean(client: AsyncClient) -> None:
    """PATCH with title: true returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": True})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- GET /todos list item shape ---


@pytest.mark.asyncio
async def test_list_todos_item_shape(client: AsyncClient) -> None:
    """GET /todos list items have exactly {id, title, completed}."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.get("/todos")
    for item in resp.json():
        assert set(item.keys()) == {"id", "title", "completed"}
