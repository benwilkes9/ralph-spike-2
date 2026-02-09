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


@pytest.mark.asyncio
async def test_put_completed_type_before_title_length(
    client: AsyncClient,
) -> None:
    """PUT: completed type error (pri 2) before title too long (pri 4)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "a" * 501, "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_patch_completed_type_before_title_length(
    client: AsyncClient,
) -> None:
    """PATCH: completed type error (pri 2) before title too long (pri 4)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "a" * 501, "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_put_title_null_before_completed_type_error(
    client: AsyncClient,
) -> None:
    """PUT: title:null (pri 1) before completed type error (pri 2)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": None, "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


@pytest.mark.asyncio
async def test_patch_title_null_and_completed_type_error(
    client: AsyncClient,
) -> None:
    """PATCH: title:null type error before completed type error."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": None, "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_put_blank_title_with_valid_completed(
    client: AsyncClient,
) -> None:
    """PUT: blank title (pri 3) reported when completed is valid bool."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "   ", "completed": True},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_patch_blank_title_with_valid_completed(
    client: AsyncClient,
) -> None:
    """PATCH: blank title (pri 3) reported when completed is valid."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "   ", "completed": True},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_put_length_before_uniqueness(client: AsyncClient) -> None:
    """PUT: title too long (pri 4) before uniqueness (pri 5)."""
    await client.post("/todos", json={"title": "a" * 500})
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "a" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


@pytest.mark.asyncio
async def test_patch_length_before_uniqueness(
    client: AsyncClient,
) -> None:
    """PATCH: title too long (pri 4) before uniqueness (pri 5)."""
    await client.post("/todos", json={"title": "a" * 500})
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": "a" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


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
    assert resp.json()["detail"] == "Invalid JSON in request body"


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
    assert resp.json()["detail"] == "Invalid JSON in request body"


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
    assert resp.json()["detail"] == "Invalid JSON in request body"


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


# --- Validation order: title null with completed present ---


@pytest.mark.asyncio
async def test_create_title_null_with_completed(
    client: AsyncClient,
) -> None:
    """POST: title:null is 'title is required' (missing), not type error."""
    resp = await client.post("/todos", json={"title": None, "completed": True})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


# --- PUT title type error before completed type error ---


@pytest.mark.asyncio
async def test_put_both_type_errors_title_first(
    client: AsyncClient,
) -> None:
    """PUT: when title and completed both have type errors, title first."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": 123, "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- PATCH title type error before completed type error ---


@pytest.mark.asyncio
async def test_patch_both_type_errors_title_first(
    client: AsyncClient,
) -> None:
    """PATCH: when title and completed both have type errors, title first."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": 123, "completed": "yes"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- Very large path ID on PUT, PATCH, complete, incomplete ---


@pytest.mark.asyncio
async def test_put_very_large_id(client: AsyncClient) -> None:
    """PUT with id exceeding SQLite range returns 422."""
    resp = await client.put("/todos/99999999999999999999", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_patch_very_large_id(client: AsyncClient) -> None:
    """PATCH with id exceeding SQLite range returns 422."""
    resp = await client.patch("/todos/99999999999999999999", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_complete_very_large_id(client: AsyncClient) -> None:
    """POST complete with very large id returns 422."""
    resp = await client.post("/todos/99999999999999999999/complete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_incomplete_very_large_id(client: AsyncClient) -> None:
    """POST incomplete with very large id returns 422."""
    resp = await client.post("/todos/99999999999999999999/incomplete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- Error response body shape: only "detail" key ---


@pytest.mark.asyncio
async def test_422_error_has_only_detail_key(client: AsyncClient) -> None:
    """422 error response body has exactly one key: detail."""
    resp = await client.post("/todos", json={})
    assert resp.status_code == 422
    assert set(resp.json().keys()) == {"detail"}


@pytest.mark.asyncio
async def test_404_error_has_only_detail_key(client: AsyncClient) -> None:
    """404 error response body has exactly one key: detail."""
    resp = await client.get("/todos/9999")
    assert resp.status_code == 404
    assert set(resp.json().keys()) == {"detail"}


@pytest.mark.asyncio
async def test_409_error_has_only_detail_key(client: AsyncClient) -> None:
    """409 error response body has exactly one key: detail."""
    await client.post("/todos", json={"title": "Dup"})
    resp = await client.post("/todos", json={"title": "Dup"})
    assert resp.status_code == 409
    assert set(resp.json().keys()) == {"detail"}


# --- Missing zero/negative ID tests ---


@pytest.mark.asyncio
async def test_put_zero_id(client: AsyncClient) -> None:
    """PUT /todos/0 returns 422."""
    resp = await client.put("/todos/0", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_patch_zero_id(client: AsyncClient) -> None:
    """PATCH /todos/0 returns 422."""
    resp = await client.patch("/todos/0", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_patch_negative_id(client: AsyncClient) -> None:
    """PATCH /todos/-1 returns 422."""
    resp = await client.patch("/todos/-1", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_complete_zero_id(client: AsyncClient) -> None:
    """POST /todos/0/complete returns 422."""
    resp = await client.post("/todos/0/complete")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_zero_id(client: AsyncClient) -> None:
    """DELETE /todos/0 returns 422."""
    resp = await client.delete("/todos/0")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_negative_id(client: AsyncClient) -> None:
    """DELETE /todos/-1 returns 422."""
    resp = await client.delete("/todos/-1")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- Unknown fields only on POST/PUT ---


@pytest.mark.asyncio
async def test_create_only_unknown_fields(client: AsyncClient) -> None:
    """POST /todos with only unknown fields returns 422."""
    resp = await client.post("/todos", json={"foo": "bar", "baz": 123})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


@pytest.mark.asyncio
async def test_put_only_unknown_fields(client: AsyncClient) -> None:
    """PUT with only unknown fields returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"foo": "bar"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"


# --- No body at all ---


@pytest.mark.asyncio
async def test_create_no_body(client: AsyncClient) -> None:
    """POST /todos with no body returns 422."""
    resp = await client.post(
        "/todos",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Invalid JSON in request body"


@pytest.mark.asyncio
async def test_put_no_body(client: AsyncClient) -> None:
    """PUT with no body returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Invalid JSON in request body"


@pytest.mark.asyncio
async def test_patch_no_body(client: AsyncClient) -> None:
    """PATCH with no body returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Invalid JSON in request body"


# --- 405 Method Not Allowed on complete/incomplete ---


@pytest.mark.asyncio
async def test_complete_get_returns_405(client: AsyncClient) -> None:
    """GET /todos/{id}/complete returns 405."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.get(f"/todos/{todo_id}/complete")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_incomplete_get_returns_405(client: AsyncClient) -> None:
    """GET /todos/{id}/incomplete returns 405."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.get(f"/todos/{todo_id}/incomplete")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_complete_put_returns_405(client: AsyncClient) -> None:
    """PUT /todos/{id}/complete returns 405."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}/complete", json={"title": "X"})
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_incomplete_delete_returns_405(client: AsyncClient) -> None:
    """DELETE /todos/{id}/incomplete returns 405."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.delete(f"/todos/{todo_id}/incomplete")
    assert resp.status_code == 405


# --- Response type validation ---


@pytest.mark.asyncio
async def test_get_response_field_types(client: AsyncClient) -> None:
    """GET /todos/{id} response fields have correct types."""
    r = await client.post("/todos", json={"title": "Type Check"})
    todo_id = r.json()["id"]
    resp = await client.get(f"/todos/{todo_id}")
    data = resp.json()
    assert isinstance(data["id"], int)
    assert isinstance(data["title"], str)
    assert isinstance(data["completed"], bool)


@pytest.mark.asyncio
async def test_put_response_field_types(client: AsyncClient) -> None:
    """PUT response fields have correct types."""
    r = await client.post("/todos", json={"title": "Type Check"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": "Updated"})
    data = resp.json()
    assert isinstance(data["id"], int)
    assert isinstance(data["title"], str)
    assert isinstance(data["completed"], bool)


@pytest.mark.asyncio
async def test_patch_response_field_types(client: AsyncClient) -> None:
    """PATCH response fields have correct types."""
    r = await client.post("/todos", json={"title": "Type Check"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": True})
    data = resp.json()
    assert isinstance(data["id"], int)
    assert isinstance(data["title"], str)
    assert isinstance(data["completed"], bool)


@pytest.mark.asyncio
async def test_complete_response_field_types(
    client: AsyncClient,
) -> None:
    """POST complete response fields have correct types."""
    r = await client.post("/todos", json={"title": "Type Check"})
    todo_id = r.json()["id"]
    resp = await client.post(f"/todos/{todo_id}/complete")
    data = resp.json()
    assert isinstance(data["id"], int)
    assert isinstance(data["title"], str)
    assert isinstance(data["completed"], bool)


@pytest.mark.asyncio
async def test_list_response_item_types(client: AsyncClient) -> None:
    """GET /todos list items have correct field types."""
    await client.post("/todos", json={"title": "Type Check"})
    resp = await client.get("/todos")
    items = resp.json()
    assert len(items) >= 1
    for item in items:
        assert isinstance(item["id"], int)
        assert isinstance(item["title"], str)
        assert isinstance(item["completed"], bool)


# --- Trim + length + uniqueness combined ---


@pytest.mark.asyncio
async def test_create_trim_length_uniqueness_combined(
    client: AsyncClient,
) -> None:
    """POST title at 500 chars after trim that is a case-insensitive dup."""
    title = "a" * 500
    await client.post("/todos", json={"title": title})
    resp = await client.post("/todos", json={"title": f"  {'A' * 500}  "})
    assert resp.status_code == 409
    assert resp.json()["detail"] == ("A todo with this title already exists")


# --- 405 Method Not Allowed on collection endpoint ---


@pytest.mark.asyncio
async def test_put_todos_collection_returns_405(
    client: AsyncClient,
) -> None:
    """PUT /todos (collection) returns 405."""
    resp = await client.put("/todos", json={"title": "Test"})
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_patch_todos_collection_returns_405(
    client: AsyncClient,
) -> None:
    """PATCH /todos (collection) returns 405."""
    resp = await client.patch("/todos", json={"title": "Test"})
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_delete_todos_collection_returns_405(
    client: AsyncClient,
) -> None:
    """DELETE /todos (collection) returns 405."""
    resp = await client.delete("/todos")
    assert resp.status_code == 405


# --- Non-dict JSON body types (number, boolean) ---


@pytest.mark.asyncio
async def test_create_json_number_body(client: AsyncClient) -> None:
    """POST /todos with JSON number body returns 422."""
    resp = await client.post(
        "/todos",
        content=b"42",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Request body must be a JSON object"


@pytest.mark.asyncio
async def test_create_json_boolean_body(client: AsyncClient) -> None:
    """POST /todos with JSON boolean body returns 422."""
    resp = await client.post(
        "/todos",
        content=b"true",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Request body must be a JSON object"


@pytest.mark.asyncio
async def test_put_json_number_body(client: AsyncClient) -> None:
    """PUT with JSON number body returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        content=b"42",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Request body must be a JSON object"


@pytest.mark.asyncio
async def test_patch_json_boolean_body(client: AsyncClient) -> None:
    """PATCH with JSON boolean body returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        content=b"false",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Request body must be a JSON object"


# --- Validation precedence: multiple invalid query params ---


@pytest.mark.asyncio
async def test_completed_error_before_sort_error(
    client: AsyncClient,
) -> None:
    """Invalid completed checked before invalid sort."""
    resp = await client.get("/todos", params={"completed": "yes", "sort": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


@pytest.mark.asyncio
async def test_sort_error_before_order_error(
    client: AsyncClient,
) -> None:
    """Invalid sort checked before invalid order."""
    resp = await client.get("/todos", params={"sort": "invalid", "order": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "sort must be 'id' or 'title'"


@pytest.mark.asyncio
async def test_page_error_before_per_page_error(
    client: AsyncClient,
) -> None:
    """Invalid page checked before invalid per_page."""
    resp = await client.get("/todos", params={"page": "abc", "per_page": "abc"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


# --- Unknown query param triggers envelope response ---


@pytest.mark.asyncio
async def test_unknown_query_param_returns_envelope(
    client: AsyncClient,
) -> None:
    """GET /todos?foo=bar returns envelope format with defaults."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.get("/todos", params={"foo": "bar"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "page" in data
    assert "per_page" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["per_page"] == 10


# --- Title float type on PUT and PATCH ---


@pytest.mark.asyncio
async def test_put_title_float(client: AsyncClient) -> None:
    """PUT with title: 3.14 returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"title": 3.14})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


@pytest.mark.asyncio
async def test_patch_title_float(client: AsyncClient) -> None:
    """PATCH with title: 3.14 returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"title": 3.14})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- Completed float/list/object types ---


@pytest.mark.asyncio
async def test_put_completed_float(client: AsyncClient) -> None:
    """PUT with completed: 3.14 returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Valid", "completed": 3.14},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_patch_completed_list(client: AsyncClient) -> None:
    """PATCH with completed: [] returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(f"/todos/{todo_id}", json={"completed": []})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


@pytest.mark.asyncio
async def test_put_completed_object(client: AsyncClient) -> None:
    """PUT with completed: {} returns 422."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "Valid", "completed": {}},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


# --- Path ID with leading zeros ---


@pytest.mark.asyncio
async def test_get_path_id_leading_zeros(client: AsyncClient) -> None:
    """GET /todos/01 resolves to todo with ID 1."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.get(f"/todos/0{todo_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id


# --- Title float type on POST ---


@pytest.mark.asyncio
async def test_create_title_float(client: AsyncClient) -> None:
    """POST /todos with title: 3.14 returns 422."""
    resp = await client.post("/todos", json={"title": 3.14})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- Path ID boundary: exactly SQLite max (2^63 - 1) ---


@pytest.mark.asyncio
async def test_get_path_id_exactly_sqlite_max(
    client: AsyncClient,
) -> None:
    """GET /todos/9223372036854775807 (2^63-1) is valid ID, returns 404."""
    resp = await client.get("/todos/9223372036854775807")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Todo not found"


@pytest.mark.asyncio
async def test_get_path_id_one_above_sqlite_max(
    client: AsyncClient,
) -> None:
    """GET /todos/9223372036854775808 (2^63) returns 422."""
    resp = await client.get("/todos/9223372036854775808")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- PATCH cross-field: completed:null + blank title ---


@pytest.mark.asyncio
async def test_patch_completed_null_before_title_blank(
    client: AsyncClient,
) -> None:
    """PATCH: completed:null (type, pri 2) before title:'' (blank, pri 3)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": "", "completed": None},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


# --- PATCH cross-field: title:null + completed:null ---


@pytest.mark.asyncio
async def test_patch_title_null_completed_null(
    client: AsyncClient,
) -> None:
    """PATCH: title:null + completed:null returns title type error first."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.patch(
        f"/todos/{todo_id}",
        json={"title": None, "completed": None},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- PUT cross-field: completed:null + title over 500 chars ---


@pytest.mark.asyncio
async def test_put_completed_null_before_title_length(
    client: AsyncClient,
) -> None:
    """PUT: completed:null (type, pri 2) before title length (pri 4)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": "a" * 501, "completed": None},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be a boolean"


# --- PUT cross-field: title:bool + completed:null ---


@pytest.mark.asyncio
async def test_put_title_bool_completed_null(
    client: AsyncClient,
) -> None:
    """PUT: title:true + completed:null returns title type error."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(
        f"/todos/{todo_id}",
        json={"title": True, "completed": None},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be a string"


# --- Path ID validation before body validation ---


@pytest.mark.asyncio
async def test_put_invalid_id_before_body_validation(
    client: AsyncClient,
) -> None:
    """PUT: invalid path id (pri 0) before missing title (pri 1)."""
    resp = await client.put("/todos/abc", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_patch_invalid_id_before_body_validation(
    client: AsyncClient,
) -> None:
    """PATCH: invalid path id (pri 0) before empty body (pri 1)."""
    resp = await client.patch("/todos/abc", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_delete_invalid_id_before_lookup(
    client: AsyncClient,
) -> None:
    """DELETE: invalid path id returns 422 not 404."""
    resp = await client.delete("/todos/-5")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


@pytest.mark.asyncio
async def test_complete_invalid_id_with_body(
    client: AsyncClient,
) -> None:
    """POST complete: zero id returns 422 regardless of body."""
    resp = await client.post("/todos/0/complete", content=b"garbage")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "id must be a positive integer"


# --- Additional 405 Method Not Allowed tests ---


@pytest.mark.asyncio
async def test_complete_patch_returns_405(client: AsyncClient) -> None:
    """PATCH /todos/{id}/complete returns 405."""
    resp = await client.patch("/todos/1/complete")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_complete_delete_returns_405(client: AsyncClient) -> None:
    """DELETE /todos/{id}/complete returns 405."""
    resp = await client.delete("/todos/1/complete")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_incomplete_put_returns_405(client: AsyncClient) -> None:
    """PUT /todos/{id}/incomplete returns 405."""
    resp = await client.put("/todos/1/incomplete", json={})
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_incomplete_patch_returns_405(client: AsyncClient) -> None:
    """PATCH /todos/{id}/incomplete returns 405."""
    resp = await client.patch("/todos/1/incomplete", json={})
    assert resp.status_code == 405


# --- Whitespace edge cases ---


@pytest.mark.asyncio
async def test_create_tab_only_title(client: AsyncClient) -> None:
    """POST with tab-only title returns 422."""
    resp = await client.post("/todos", json={"title": "\t\t"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_create_newline_only_title(client: AsyncClient) -> None:
    """POST with newline-only title returns 422."""
    resp = await client.post("/todos", json={"title": "\n\n"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_create_long_whitespace_only_title(
    client: AsyncClient,
) -> None:
    """POST with 600 spaces returns blank error (not length error).

    Trim first → empty → blank check fires before length check.
    """
    resp = await client.post("/todos", json={"title": " " * 600})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must not be blank"


@pytest.mark.asyncio
async def test_create_title_501_after_trim(client: AsyncClient) -> None:
    """POST with 501 chars after trim returns length error."""
    title = " " + "a" * 501 + " "
    resp = await client.post("/todos", json={"title": title})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title must be 500 characters or fewer"


# --- POST /todos/{id} returns 405 ---


@pytest.mark.asyncio
async def test_post_single_todo_returns_405(client: AsyncClient) -> None:
    """POST /todos/{id} (not complete/incomplete) returns 405."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.post(f"/todos/{todo_id}")
    assert resp.status_code == 405


# --- 405 response body format ---


@pytest.mark.asyncio
async def test_405_response_has_detail_key(client: AsyncClient) -> None:
    """405 responses use the standard {"detail": "..."} error format."""
    resp = await client.put("/todos", json={"title": "Test"})
    assert resp.status_code == 405
    data = resp.json()
    assert set(data.keys()) == {"detail"}
    assert isinstance(data["detail"], str)


# --- PUT with only completed:null (no title) ---


@pytest.mark.asyncio
async def test_put_completed_null_only_returns_title_required(
    client: AsyncClient,
) -> None:
    """PUT with only completed:null returns title is required (pri 1)."""
    r = await client.post("/todos", json={"title": "Test"})
    todo_id = r.json()["id"]
    resp = await client.put(f"/todos/{todo_id}", json={"completed": None})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "title is required"
