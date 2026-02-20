"""Tests for Task 4: Retrieve Todos Endpoints (GET /todos, GET /todos/{id})."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.testclient import TestClient


class TestListTodos:
    """Tests for GET /todos."""

    def test_empty_list(self, client: TestClient) -> None:
        """GET /todos with no todos returns 200 with []."""
        resp = client.get("/todos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_ordered_by_id_desc(self, client: TestClient) -> None:
        """GET /todos with 3 todos returns 200 with all 3, ordered by id descending."""
        client.post("/todos", json={"title": "First"})
        client.post("/todos", json={"title": "Second"})
        client.post("/todos", json={"title": "Third"})

        resp = client.get("/todos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Newest first (highest id first)
        assert data[0]["title"] == "Third"
        assert data[1]["title"] == "Second"
        assert data[2]["title"] == "First"
        # IDs should be descending
        assert data[0]["id"] > data[1]["id"] > data[2]["id"]


class TestGetTodo:
    """Tests for GET /todos/{id}."""

    def test_get_existing_todo(self, client: TestClient) -> None:
        """GET /todos/1 returns 200 with the matching todo object."""
        create_resp = client.post("/todos", json={"title": "Buy milk"})
        todo_id = create_resp.json()["id"]

        resp = client.get(f"/todos/{todo_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == todo_id
        assert data["title"] == "Buy milk"
        assert data["completed"] is False

    def test_not_found(self, client: TestClient) -> None:
        """GET /todos/999 (non-existent) returns 404 with detail."""
        resp = client.get("/todos/999")
        assert resp.status_code == 404
        assert resp.json() == {"detail": "Todo not found"}

    def test_non_integer_id(self, client: TestClient) -> None:
        """GET /todos/abc (non-integer) returns 422 with detail."""
        resp = client.get("/todos/abc")
        assert resp.status_code == 422
        assert resp.json() == {"detail": "id must be a positive integer"}

    def test_zero_id(self, client: TestClient) -> None:
        """GET /todos/0 returns 422 (not a positive integer)."""
        resp = client.get("/todos/0")
        assert resp.status_code == 422
        assert resp.json() == {"detail": "id must be a positive integer"}

    def test_negative_id(self, client: TestClient) -> None:
        """GET /todos/-1 returns 422 (not a positive integer)."""
        resp = client.get("/todos/-1")
        assert resp.status_code == 422
        assert resp.json() == {"detail": "id must be a positive integer"}
