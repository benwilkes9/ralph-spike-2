"""Tests for PUT /todos/{id} endpoint (Task 5)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.testclient import TestClient


def _create_todo(client: TestClient, title: str = "Test todo") -> dict[str, Any]:
    """Helper to create a todo and return the response JSON."""
    resp = client.post("/todos", json={"title": title})
    assert resp.status_code == 201
    return resp.json()


class TestPutTodoBasic:
    """Basic PUT update behavior."""

    def test_put_updates_title_and_resets_completed(self, client: TestClient) -> None:
        todo = _create_todo(client, "Original title")
        # First mark it completed via a second PUT
        resp = client.put(
            f"/todos/{todo['id']}",
            json={"title": "Original title", "completed": True},
        )
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

        # PUT with only title resets completed to false
        resp = client.put(
            f"/todos/{todo['id']}", json={"title": "New title"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New title"
        assert data["completed"] is False

    def test_put_with_completed_true(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(
            f"/todos/{todo['id']}",
            json={"title": "New title", "completed": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New title"
        assert data["completed"] is True

    def test_put_omitting_completed_resets_to_false(
        self, client: TestClient
    ) -> None:
        todo = _create_todo(client)
        # Set completed to true
        client.put(
            f"/todos/{todo['id']}",
            json={"title": "Test todo", "completed": True},
        )
        # PUT without completed resets to false
        resp = client.put(
            f"/todos/{todo['id']}", json={"title": "Test todo"}
        )
        assert resp.status_code == 200
        assert resp.json()["completed"] is False


class TestPutTodoValidation:
    """PUT validation error cases."""

    def test_put_missing_title(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={"completed": True})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title is required"

    def test_put_blank_title(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={"title": ""})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_put_whitespace_only_title(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(f"/todos/{todo['id']}", json={"title": "   "})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_put_title_exceeds_500_chars(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(
            f"/todos/{todo['id']}", json={"title": "a" * 501}
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be 500 characters or fewer"

    def test_put_title_exactly_500_chars(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(
            f"/todos/{todo['id']}", json={"title": "a" * 500}
        )
        assert resp.status_code == 200
        assert len(resp.json()["title"]) == 500


class TestPutTodoUniqueness:
    """PUT uniqueness constraint tests."""

    def test_put_duplicate_title_different_todo(
        self, client: TestClient
    ) -> None:
        _create_todo(client, "Existing title")
        todo2 = _create_todo(client, "Another title")
        resp = client.put(
            f"/todos/{todo2['id']}", json={"title": "existing title"}
        )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "A todo with this title already exists"

    def test_put_same_title_same_todo_succeeds(
        self, client: TestClient
    ) -> None:
        todo = _create_todo(client, "My title")
        resp = client.put(
            f"/todos/{todo['id']}", json={"title": "My title"}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "My title"


class TestPutTodoIdValidation:
    """PUT id validation."""

    def test_put_nonexistent_id(self, client: TestClient) -> None:
        resp = client.put("/todos/999", json={"title": "New title"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    def test_put_non_integer_id(self, client: TestClient) -> None:
        resp = client.put("/todos/abc", json={"title": "New title"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"


class TestPutTodoTrimming:
    """PUT title trimming behavior."""

    def test_put_trims_title(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(
            f"/todos/{todo['id']}", json={"title": "  hello  "}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "hello"

    def test_put_unknown_fields_ignored(self, client: TestClient) -> None:
        todo = _create_todo(client)
        resp = client.put(
            f"/todos/{todo['id']}",
            json={"title": "Updated", "foo": "bar"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
