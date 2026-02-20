"""Tests for DELETE /todos/{id} (Task 8)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.testclient import TestClient


def _create_todo(client: TestClient, title: str = "Test todo") -> dict[str, Any]:
    """Helper to create a todo and return the response JSON."""
    resp = client.post("/todos", json={"title": title})
    assert resp.status_code == 201
    return resp.json()


class TestDeleteTodo:
    """DELETE /todos/{id} endpoint tests."""

    def test_delete_existing_todo_returns_204(self, client: TestClient) -> None:
        """DELETE on existing todo returns 204 with empty body."""
        todo = _create_todo(client)
        resp = client.delete(f"/todos/{todo['id']}")
        assert resp.status_code == 204
        assert resp.content == b""

    def test_deleted_todo_not_retrievable(self, client: TestClient) -> None:
        """The deleted todo is no longer retrievable via GET /todos/{id}."""
        todo = _create_todo(client)
        client.delete(f"/todos/{todo['id']}")

        resp = client.get(f"/todos/{todo['id']}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    def test_delete_nonexistent_id(self, client: TestClient) -> None:
        """DELETE on non-existent id returns 404."""
        resp = client.delete("/todos/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    def test_delete_non_integer_id(self, client: TestClient) -> None:
        """DELETE on non-integer id returns 422."""
        resp = client.delete("/todos/abc")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_delete_zero_id(self, client: TestClient) -> None:
        """DELETE on id=0 returns 422."""
        resp = client.delete("/todos/0")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_delete_negative_id(self, client: TestClient) -> None:
        """DELETE on id=-1 returns 422."""
        resp = client.delete("/todos/-1")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"
