"""Tests for Task 10: Error Handling & Validation Consistency.

Cross-cutting integration tests that verify error response format
and validation order across all endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.testclient import TestClient


def _create_todo(client: TestClient, title: str = "Test todo") -> dict[str, Any]:
    """Helper to create a todo and return the response JSON."""
    resp = client.post("/todos", json={"title": title})
    assert resp.status_code == 201
    return resp.json()


def _assert_detail_string(response: Any) -> None:
    """Assert that the response body is {"detail": "<string>"}."""
    data = response.json()
    assert "detail" in data, f"Missing 'detail' key in response: {data}"
    assert isinstance(
        data["detail"], str
    ), f"Expected string, got {type(data['detail'])}"
    # Must not be an array (FastAPI default) or nested object
    assert not isinstance(data["detail"], list)
    assert not isinstance(data["detail"], dict)


class TestDetailFormatConsistency:
    """All error responses across all endpoints use {"detail": "..."} format."""

    # --- POST /todos errors ---

    def test_post_missing_title_format(self, client: TestClient) -> None:
        resp = client.post("/todos", json={})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_post_blank_title_format(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": ""})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_post_title_too_long_format(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "a" * 501})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_post_duplicate_title_format(self, client: TestClient) -> None:
        _create_todo(client, "Dup")
        resp = client.post("/todos", json={"title": "Dup"})
        assert resp.status_code == 409
        _assert_detail_string(resp)

    def test_post_wrong_type_title_format(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": 123})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_post_malformed_json_format(self, client: TestClient) -> None:
        resp = client.post(
            "/todos",
            content=b"{bad json}",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        _assert_detail_string(resp)

    # --- GET /todos/{id} errors ---

    def test_get_nonexistent_format(self, client: TestClient) -> None:
        resp = client.get("/todos/999")
        assert resp.status_code == 404
        _assert_detail_string(resp)

    def test_get_non_integer_id_format(self, client: TestClient) -> None:
        resp = client.get("/todos/abc")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_get_zero_id_format(self, client: TestClient) -> None:
        resp = client.get("/todos/0")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_get_negative_id_format(self, client: TestClient) -> None:
        resp = client.get("/todos/-1")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    # --- PUT /todos/{id} errors ---

    def test_put_missing_title_format(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_put_blank_title_format(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={"title": ""})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_put_title_too_long_format(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={"title": "a" * 501})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_put_duplicate_title_format(self, client: TestClient) -> None:
        _create_todo(client, "Existing")
        todo2 = _create_todo(client, "Other")
        resp = client.put(f"/todos/{todo2['id']}", json={"title": "Existing"})
        assert resp.status_code == 409
        _assert_detail_string(resp)

    def test_put_nonexistent_id_format(self, client: TestClient) -> None:
        resp = client.put("/todos/999", json={"title": "X"})
        assert resp.status_code == 404
        _assert_detail_string(resp)

    def test_put_non_integer_id_format(self, client: TestClient) -> None:
        resp = client.put("/todos/abc", json={"title": "X"})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    # --- PATCH /todos/{id} errors ---

    def test_patch_empty_body_format(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_patch_blank_title_format(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={"title": "   "})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_patch_title_too_long_format(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={"title": "a" * 501})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_patch_duplicate_title_format(self, client: TestClient) -> None:
        _create_todo(client, "Existing")
        todo2 = _create_todo(client, "Other")
        resp = client.patch(f"/todos/{todo2['id']}", json={"title": "Existing"})
        assert resp.status_code == 409
        _assert_detail_string(resp)

    def test_patch_nonexistent_id_format(self, client: TestClient) -> None:
        resp = client.patch("/todos/999", json={"completed": True})
        assert resp.status_code == 404
        _assert_detail_string(resp)

    def test_patch_non_integer_id_format(self, client: TestClient) -> None:
        resp = client.patch("/todos/abc", json={"completed": True})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    # --- POST /todos/{id}/complete errors ---

    def test_complete_nonexistent_format(self, client: TestClient) -> None:
        resp = client.post("/todos/999/complete")
        assert resp.status_code == 404
        _assert_detail_string(resp)

    def test_complete_non_integer_id_format(self, client: TestClient) -> None:
        resp = client.post("/todos/abc/complete")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    # --- POST /todos/{id}/incomplete errors ---

    def test_incomplete_nonexistent_format(self, client: TestClient) -> None:
        resp = client.post("/todos/999/incomplete")
        assert resp.status_code == 404
        _assert_detail_string(resp)

    def test_incomplete_non_integer_id_format(self, client: TestClient) -> None:
        resp = client.post("/todos/abc/incomplete")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    # --- DELETE /todos/{id} errors ---

    def test_delete_nonexistent_format(self, client: TestClient) -> None:
        resp = client.delete("/todos/999")
        assert resp.status_code == 404
        _assert_detail_string(resp)

    def test_delete_non_integer_id_format(self, client: TestClient) -> None:
        resp = client.delete("/todos/abc")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    # --- GET /todos query param errors ---

    def test_list_invalid_completed_format(self, client: TestClient) -> None:
        resp = client.get("/todos?completed=maybe")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_list_invalid_sort_format(self, client: TestClient) -> None:
        resp = client.get("/todos?sort=invalid")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_list_invalid_order_format(self, client: TestClient) -> None:
        resp = client.get("/todos?order=invalid")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_list_invalid_page_format(self, client: TestClient) -> None:
        resp = client.get("/todos?page=abc")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_list_invalid_per_page_format(self, client: TestClient) -> None:
        resp = client.get("/todos?per_page=abc")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_list_page_zero_format(self, client: TestClient) -> None:
        resp = client.get("/todos?page=0")
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_list_per_page_zero_format(self, client: TestClient) -> None:
        resp = client.get("/todos?per_page=0")
        assert resp.status_code == 422
        _assert_detail_string(resp)


class TestValidationPriorityOrder:
    """A request triggering multiple validation errors returns only the first
    per the priority order: missing → type → blank → length → uniqueness."""

    def test_post_missing_before_everything(self, client: TestClient) -> None:
        """Missing title takes priority over all other errors."""
        resp = client.post("/todos", json={})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title is required"

    def test_post_type_before_blank(self, client: TestClient) -> None:
        """Type error (title: 123) takes priority over blank/length checks."""
        resp = client.post("/todos", json={"title": 123})
        assert resp.status_code == 422
        # Should be a type error, not blank or length
        detail = resp.json()["detail"]
        assert (
            "must be a string" in detail
            or "type" in detail.lower()
            or "string" in detail.lower()
        )

    def test_post_blank_before_length(self, client: TestClient) -> None:
        """Blank title takes priority over length check.

        A whitespace-only title (which is effectively blank) should return
        the 'must not be blank' error, not a length error.
        """
        resp = client.post("/todos", json={"title": "   "})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_post_length_before_uniqueness(self, client: TestClient) -> None:
        """Length error takes priority over uniqueness.

        Create a todo, then try to create another with an extremely long
        title that would also be a duplicate — length should be reported first.
        """
        long_title = "a" * 501
        # Create one with max-length title
        _create_todo(client, "a" * 500)
        # Now try with title that's too long and a prefix-match
        resp = client.post("/todos", json={"title": long_title})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be 500 characters or fewer"

    def test_put_missing_before_everything(self, client: TestClient) -> None:
        """PUT with missing title returns 'title is required'."""
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title is required"

    def test_put_blank_before_length(self, client: TestClient) -> None:
        """PUT with blank title returns blank error, not length error."""
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={"title": ""})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_put_length_before_uniqueness(self, client: TestClient) -> None:
        """PUT with title >500 chars returns length error even if duplicate."""
        _create_todo(client, "a" * 500)
        todo2 = _create_todo(client, "Something else")
        resp = client.put(f"/todos/{todo2['id']}", json={"title": "a" * 501})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be 500 characters or fewer"

    def test_patch_blank_before_length(self, client: TestClient) -> None:
        """PATCH with blank title returns blank error, not length error."""
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={"title": ""})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_patch_length_before_uniqueness(self, client: TestClient) -> None:
        """PATCH with title >500 chars returns length error even if duplicate."""
        _create_todo(client, "a" * 500)
        todo2 = _create_todo(client, "Something else")
        resp = client.patch(f"/todos/{todo2['id']}", json={"title": "a" * 501})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be 500 characters or fewer"


class TestUnknownFieldsIgnored:
    """Unknown fields in request bodies are silently ignored across all endpoints."""

    def test_post_ignores_unknown_fields(self, client: TestClient) -> None:
        resp = client.post(
            "/todos",
            json={"title": "My task", "foo": "bar", "baz": 123},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "foo" not in data
        assert "baz" not in data

    def test_put_ignores_unknown_fields(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(
            f"/todos/{todo['id']}",
            json={"title": "Updated", "unknown": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "unknown" not in data

    def test_patch_ignores_unknown_with_valid_field(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.patch(
            f"/todos/{todo['id']}",
            json={"completed": True, "extra": "value"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "extra" not in data

    def test_patch_only_unknown_fields_returns_422(self, client: TestClient) -> None:
        """PATCH with only unknown fields returns 422."""
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={"foo": "bar"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "At least one field must be provided"


class TestTypeMismatches:
    """Type mismatches on recognized fields return 422."""

    def test_post_title_integer(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": 123})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_post_title_boolean(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": True})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_post_title_list(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": ["a", "b"]})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_put_title_integer(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={"title": 456})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_put_completed_string(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(
            f"/todos/{todo['id']}", json={"title": "X", "completed": "yes"}
        )
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_patch_completed_string(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={"completed": "yes"})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_patch_title_integer(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={"title": 789})
        assert resp.status_code == 422
        _assert_detail_string(resp)

    def test_patch_completed_integer(self, client: TestClient) -> None:
        """Integer for a StrictBool field should return 422."""
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={"completed": 1})
        assert resp.status_code == 422
        _assert_detail_string(resp)
