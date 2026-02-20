"""Tests for POST /todos/{id}/complete and POST /todos/{id}/incomplete (Task 7)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.testclient import TestClient


def _create_todo(client: TestClient, title: str = "Test todo") -> dict[str, Any]:
    """Helper to create a todo and return the response JSON."""
    resp = client.post("/todos", json={"title": title})
    assert resp.status_code == 201
    return resp.json()


def _mark_completed(client: TestClient, todo_id: int) -> None:
    """Helper to mark a todo as completed via PUT."""
    resp = client.get(f"/todos/{todo_id}")
    todo = resp.json()
    client.put(
        f"/todos/{todo_id}",
        json={"title": todo["title"], "completed": True},
    )


class TestCompleteTodo:
    """POST /todos/{id}/complete endpoint tests."""

    def test_complete_incomplete_todo(self, client: TestClient) -> None:
        """Completing an incomplete todo returns 200 with completed: true."""
        todo = _create_todo(client)
        assert todo["completed"] is False

        resp = client.post(f"/todos/{todo['id']}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == todo["id"]
        assert data["title"] == todo["title"]
        assert data["completed"] is True

    def test_complete_already_complete_todo(self, client: TestClient) -> None:
        """Completing an already-complete todo returns 200 (idempotent)."""
        todo = _create_todo(client)
        _mark_completed(client, todo["id"])

        resp = client.post(f"/todos/{todo['id']}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is True

    def test_complete_nonexistent_id(self, client: TestClient) -> None:
        """POST /todos/999/complete returns 404."""
        resp = client.post("/todos/999/complete")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    def test_complete_non_integer_id(self, client: TestClient) -> None:
        """POST /todos/abc/complete returns 422."""
        resp = client.post("/todos/abc/complete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_complete_zero_id(self, client: TestClient) -> None:
        """POST /todos/0/complete returns 422."""
        resp = client.post("/todos/0/complete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_complete_negative_id(self, client: TestClient) -> None:
        """POST /todos/-1/complete returns 422."""
        resp = client.post("/todos/-1/complete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"


class TestIncompleteTodo:
    """POST /todos/{id}/incomplete endpoint tests."""

    def test_incomplete_complete_todo(self, client: TestClient) -> None:
        """Marking a complete todo incomplete returns 200 with completed: false."""
        todo = _create_todo(client)
        _mark_completed(client, todo["id"])

        resp = client.post(f"/todos/{todo['id']}/incomplete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == todo["id"]
        assert data["title"] == todo["title"]
        assert data["completed"] is False

    def test_incomplete_already_incomplete_todo(self, client: TestClient) -> None:
        """Marking an already-incomplete todo incomplete returns 200 (idempotent)."""
        todo = _create_todo(client)
        assert todo["completed"] is False

        resp = client.post(f"/todos/{todo['id']}/incomplete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is False

    def test_incomplete_nonexistent_id(self, client: TestClient) -> None:
        """POST /todos/999/incomplete returns 404."""
        resp = client.post("/todos/999/incomplete")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    def test_incomplete_non_integer_id(self, client: TestClient) -> None:
        """POST /todos/abc/incomplete returns 422."""
        resp = client.post("/todos/abc/incomplete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_incomplete_zero_id(self, client: TestClient) -> None:
        """POST /todos/0/incomplete returns 422."""
        resp = client.post("/todos/0/incomplete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_incomplete_negative_id(self, client: TestClient) -> None:
        """POST /todos/-1/incomplete returns 422."""
        resp = client.post("/todos/-1/incomplete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"
