"""Tests for Task 3: Create Todo Endpoint (POST /todos)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.testclient import TestClient


def test_create_todo_valid(client: TestClient) -> None:
    """Valid POST with {"title": "Buy milk"} returns 201 with the todo object."""
    response = client.post("/todos", json={"title": "Buy milk"})
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data["id"], int)
    assert data["title"] == "Buy milk"
    assert data["completed"] is False


def test_create_todo_unique_id(client: TestClient) -> None:
    """The returned id is a unique auto-generated integer."""
    r1 = client.post("/todos", json={"title": "Task A"})
    r2 = client.post("/todos", json={"title": "Task B"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]
    assert isinstance(r1.json()["id"], int)
    assert isinstance(r2.json()["id"], int)


def test_create_todo_completed_always_false(client: TestClient) -> None:
    """completed is always false on the returned object, even if true is sent."""
    response = client.post("/todos", json={"title": "X", "completed": True})
    assert response.status_code == 201
    assert response.json()["completed"] is False


def test_create_todo_missing_title(client: TestClient) -> None:
    """POST with missing title field returns 422."""
    response = client.post("/todos", json={})
    assert response.status_code == 422
    assert response.json() == {"detail": "title is required"}


def test_create_todo_empty_title(client: TestClient) -> None:
    """POST with empty title returns 422."""
    response = client.post("/todos", json={"title": ""})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must not be blank"}


def test_create_todo_whitespace_only_title(client: TestClient) -> None:
    """POST with whitespace-only title returns 422."""
    response = client.post("/todos", json={"title": "   "})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must not be blank"}


def test_create_todo_title_too_long(client: TestClient) -> None:
    """POST with a title of 501 characters returns 422."""
    long_title = "a" * 501
    response = client.post("/todos", json={"title": long_title})
    assert response.status_code == 422
    assert response.json() == {"detail": "title must be 500 characters or fewer"}


def test_create_todo_title_exactly_500_chars(client: TestClient) -> None:
    """POST with a title of exactly 500 characters returns 201."""
    title = "a" * 500
    response = client.post("/todos", json={"title": title})
    assert response.status_code == 201
    assert response.json()["title"] == title


def test_create_todo_duplicate_case_insensitive(client: TestClient) -> None:
    """Creating duplicate title (case-insensitive) returns 409."""
    r1 = client.post("/todos", json={"title": "Buy milk"})
    assert r1.status_code == 201
    r2 = client.post("/todos", json={"title": "buy milk"})
    assert r2.status_code == 409
    assert r2.json() == {"detail": "A todo with this title already exists"}


def test_create_todo_title_trimmed(client: TestClient) -> None:
    """POST with padded title stores and returns trimmed value."""
    response = client.post("/todos", json={"title": "  hello  "})
    assert response.status_code == 201
    assert response.json()["title"] == "hello"


def test_create_todo_trimmed_length_boundary(client: TestClient) -> None:
    """POST with title of 502 chars (2 spaces + 500 content) returns 201."""
    title = " " + "a" * 500 + " "
    response = client.post("/todos", json={"title": title})
    assert response.status_code == 201
    assert response.json()["title"] == "a" * 500


def test_create_todo_trimmed_uniqueness(client: TestClient) -> None:
    """Creating padded duplicate after existing returns 409."""
    r1 = client.post("/todos", json={"title": "Buy milk"})
    assert r1.status_code == 201
    r2 = client.post("/todos", json={"title": "  Buy milk  "})
    assert r2.status_code == 409
    assert r2.json() == {"detail": "A todo with this title already exists"}


def test_create_todo_unknown_fields_ignored(client: TestClient) -> None:
    """Unknown fields in the request body are silently ignored."""
    response = client.post("/todos", json={"title": "Test", "foo": "bar"})
    assert response.status_code == 201
    data = response.json()
    assert "foo" not in data
    assert data["title"] == "Test"


def test_create_todo_wrong_type_title(client: TestClient) -> None:
    """POST with title as wrong type (integer) returns 422."""
    response = client.post("/todos", json={"title": 123})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)
