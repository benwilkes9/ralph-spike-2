"""Tests for PATCH /todos/{id} endpoint (Task 6)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.testclient import TestClient


def _create_todo(client: TestClient, title: str = "Test todo") -> dict[str, Any]:
    """Helper to create a todo and return the response JSON."""
    resp = client.post("/todos", json={"title": title})
    assert resp.status_code == 201
    return resp.json()


class TestPatchTodoBasic:
    """Basic PATCH partial-update behavior."""

    def test_patch_completed_only(self, client: TestClient) -> None:
        """PATCH with completed only leaves title unchanged."""
        todo = _create_todo(client, "Original title")
        resp = client.patch(
            f"/todos/{todo['id']}", json={"completed": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Original title"
        assert data["completed"] is True

    def test_patch_title_only(self, client: TestClient) -> None:
        """PATCH with title only leaves completed unchanged."""
        todo = _create_todo(client, "Original")
        # First set completed to true via PUT
        client.put(
            f"/todos/{todo['id']}",
            json={"title": "Original", "completed": True},
        )
        # Now PATCH only the title
        resp = client.patch(
            f"/todos/{todo['id']}", json={"title": "Updated"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated"
        assert data["completed"] is True  # unchanged

    def test_patch_both_fields(self, client: TestClient) -> None:
        """PATCH with both title and completed updates both fields."""
        todo = _create_todo(client, "Original")
        resp = client.patch(
            f"/todos/{todo['id']}",
            json={"title": "Updated", "completed": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated"
        assert data["completed"] is True


class TestPatchTodoValidation:
    """PATCH validation error cases."""

    def test_patch_empty_body(self, client: TestClient) -> None:
        """PATCH with empty body {} returns 422."""
        todo = _create_todo(client)
        resp = client.patch(f"/todos/{todo['id']}", json={})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "At least one field must be provided"

    def test_patch_only_unknown_fields(self, client: TestClient) -> None:
        """PATCH with only unknown fields returns 422."""
        todo = _create_todo(client)
        resp = client.patch(
            f"/todos/{todo['id']}", json={"foo": "bar"}
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "At least one field must be provided"

    def test_patch_whitespace_only_title(self, client: TestClient) -> None:
        """PATCH with {"title": "   "} returns 422."""
        todo = _create_todo(client)
        resp = client.patch(
            f"/todos/{todo['id']}", json={"title": "   "}
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_patch_title_exceeds_500_chars(self, client: TestClient) -> None:
        """PATCH with title exceeding 500 chars returns 422."""
        todo = _create_todo(client)
        resp = client.patch(
            f"/todos/{todo['id']}", json={"title": "a" * 501}
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be 500 characters or fewer"

    def test_patch_completed_wrong_type(self, client: TestClient) -> None:
        """PATCH with {"completed": "yes"} (wrong type) returns 422."""
        todo = _create_todo(client)
        resp = client.patch(
            f"/todos/{todo['id']}", json={"completed": "yes"}
        )
        assert resp.status_code == 422


class TestPatchTodoUniqueness:
    """PATCH uniqueness constraint tests."""

    def test_patch_duplicate_title_different_todo(
        self, client: TestClient
    ) -> None:
        """PATCH with duplicate title (case-insensitive, different todo) returns 409."""
        _create_todo(client, "Existing title")
        todo2 = _create_todo(client, "Another title")
        resp = client.patch(
            f"/todos/{todo2['id']}", json={"title": "existing title"}
        )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "A todo with this title already exists"


class TestPatchTodoIdValidation:
    """PATCH id validation."""

    def test_patch_nonexistent_id(self, client: TestClient) -> None:
        """PATCH on non-existent id returns 404."""
        resp = client.patch("/todos/999", json={"completed": True})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    def test_patch_non_integer_id(self, client: TestClient) -> None:
        """PATCH on non-integer id returns 422."""
        resp = client.patch("/todos/abc", json={"completed": True})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"


class TestPatchTodoTrimming:
    """PATCH title trimming behavior."""

    def test_patch_trims_title(self, client: TestClient) -> None:
        """Title is trimmed when provided."""
        todo = _create_todo(client)
        resp = client.patch(
            f"/todos/{todo['id']}", json={"title": "  hello  "}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "hello"
