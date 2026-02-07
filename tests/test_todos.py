"""Comprehensive tests for Todo CRUD API."""

from __future__ import annotations

import os

# Use named shared in-memory database for tests
_TEST_DB_URL = "sqlite:///file:test_db?mode=memory&cache=shared"
os.environ["DATABASE_URL"] = _TEST_DB_URL

from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from ralf_spike_2 import database as db  # noqa: E402
from ralf_spike_2.app import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db() -> Any:  # pyright: ignore[reportUnusedFunction]
    """Reset database before each test using shared in-memory SQLite."""
    db.close_connection()
    db.DATABASE_URL = _TEST_DB_URL
    db.init_db()
    # Clean any leftover data from previous tests
    conn = db.get_connection()
    conn.execute("DELETE FROM todos")
    # Reset autoincrement counter for clean test isolation
    conn.execute("DELETE FROM sqlite_sequence WHERE name='todos'")
    conn.commit()
    yield
    db.close_connection()


@pytest.fixture()
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


# ============================================================
# Task 1: App is importable and creates a FastAPI instance
# ============================================================


class TestAppSetup:
    def test_app_is_importable(self) -> None:
        from ralf_spike_2.app import app as _app

        assert _app is not None

    def test_app_is_fastapi_instance(self) -> None:
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)


# ============================================================
# Task 2: Database Layer & Todo Model
# ============================================================


class TestDatabase:
    def test_table_created_on_init(self) -> None:
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='todos'"
        )
        assert cursor.fetchone() is not None

    def test_id_is_auto_generated_integer(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "Test"})
        data = resp.json()
        assert isinstance(data["id"], int)

    def test_title_uniqueness_case_insensitive_db_level(self) -> None:
        db.create_todo("Buy milk")
        import sqlite3

        with pytest.raises(sqlite3.IntegrityError):
            db.create_todo("buy milk")

    def test_completed_defaults_to_false(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "Test"})
        assert resp.json()["completed"] is False

    def test_title_stored_trimmed(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "  hello  "})
        assert resp.json()["title"] == "hello"


# ============================================================
# Task 3: Create Todo — POST /todos
# ============================================================


class TestCreateTodo:
    def test_valid_post_creates_todo_returns_201(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "Buy groceries"})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["title"] == "Buy groceries"
        assert data["completed"] is False

    def test_returned_id_is_unique_auto_integer(self, client: TestClient) -> None:
        r1 = client.post("/todos", json={"title": "First"})
        r2 = client.post("/todos", json={"title": "Second"})
        assert isinstance(r1.json()["id"], int)
        assert isinstance(r2.json()["id"], int)
        assert r1.json()["id"] != r2.json()["id"]

    def test_completed_always_false(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "Test", "completed": True})
        assert resp.json()["completed"] is False

    def test_case_insensitive_duplicate_rejected_409(self, client: TestClient) -> None:
        client.post("/todos", json={"title": "Buy milk"})
        resp = client.post("/todos", json={"title": "buy milk"})
        assert resp.status_code == 409
        assert resp.json()["detail"] == "A todo with this title already exists"

    def test_whitespace_only_title_rejected_422(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "   "})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_missing_title_returns_422(self, client: TestClient) -> None:
        resp = client.post("/todos", json={})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title is required"

    def test_title_over_500_chars_rejected(self, client: TestClient) -> None:
        long_title = "a" * 501
        resp = client.post("/todos", json={"title": long_title})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be 500 characters or fewer"

    def test_leading_trailing_whitespace_trimmed(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "  trimmed  "})
        assert resp.status_code == 201
        assert resp.json()["title"] == "trimmed"

    def test_unknown_fields_silently_ignored(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "Test", "unknown": "field"})
        assert resp.status_code == 201
        assert "unknown" not in resp.json()


# ============================================================
# Task 4: Retrieve Todos — GET /todos and GET /todos/{id}
# ============================================================


class TestRetrieveTodos:
    def test_get_all_returns_200_with_todos(self, client: TestClient) -> None:
        client.post("/todos", json={"title": "Todo 1"})
        client.post("/todos", json={"title": "Todo 2"})
        resp = client.get("/todos")
        assert resp.status_code == 200
        data: list[dict[str, Any]] = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_all_returns_empty_list(self, client: TestClient) -> None:
        resp = client.get("/todos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_all_newest_first(self, client: TestClient) -> None:
        client.post("/todos", json={"title": "First"})
        client.post("/todos", json={"title": "Second"})
        client.post("/todos", json={"title": "Third"})
        resp = client.get("/todos")
        data = resp.json()
        assert data[0]["title"] == "Third"
        assert data[1]["title"] == "Second"
        assert data[2]["title"] == "First"

    def test_get_by_id_returns_200(self, client: TestClient) -> None:
        create_resp = client.post("/todos", json={"title": "Test"})
        todo_id = create_resp.json()["id"]
        resp = client.get(f"/todos/{todo_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == todo_id
        assert resp.json()["title"] == "Test"

    def test_get_by_id_not_found_404(self, client: TestClient) -> None:
        resp = client.get("/todos/9999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    def test_get_by_id_non_integer_422(self, client: TestClient) -> None:
        resp = client.get("/todos/abc")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_get_by_id_zero_returns_422(self, client: TestClient) -> None:
        resp = client.get("/todos/0")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_get_by_id_negative_returns_422(self, client: TestClient) -> None:
        resp = client.get("/todos/-1")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    def test_newest_first_ordering_verified(self, client: TestClient) -> None:
        for i in range(5):
            client.post("/todos", json={"title": f"Todo {i}"})
        resp = client.get("/todos")
        data = resp.json()
        ids = [t["id"] for t in data]
        assert ids == sorted(ids, reverse=True)


# ============================================================
# Task 5: Update Todo — PUT /todos/{id}
# ============================================================


class TestUpdateTodoPut:
    def test_put_replaces_title_and_completed(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Original"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "Updated", "completed": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated"
        assert data["completed"] is True

    def test_put_omitting_completed_resets_to_false(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        # Mark complete
        client.post(f"/todos/{tid}/complete")
        # PUT without completed
        resp = client.put(f"/todos/{tid}", json={"title": "Test"})
        assert resp.json()["completed"] is False

    def test_put_duplicate_title_409(self, client: TestClient) -> None:
        client.post("/todos", json={"title": "First"})
        r2 = client.post("/todos", json={"title": "Second"})
        tid = r2.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "first"})
        assert resp.status_code == 409

    def test_put_same_title_succeeds(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Same"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "Same"})
        assert resp.status_code == 200

    def test_put_whitespace_title_422(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "  "})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    def test_put_title_over_500_422(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "a" * 501})
        assert resp.status_code == 422

    def test_put_missing_title_422(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"completed": True})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title is required"

    def test_put_nonexistent_id_404(self, client: TestClient) -> None:
        resp = client.put("/todos/9999", json={"title": "Test"})
        assert resp.status_code == 404

    def test_put_non_integer_id_422(self, client: TestClient) -> None:
        resp = client.put("/todos/abc", json={"title": "Test"})
        assert resp.status_code == 422

    def test_put_title_trimmed(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "  Updated  "})
        assert resp.json()["title"] == "Updated"

    def test_put_unknown_fields_ignored(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "Updated", "foo": "bar"})
        assert resp.status_code == 200


# ============================================================
# Task 6: Update Todo — PATCH /todos/{id}
# ============================================================


class TestUpdateTodoPatch:
    def test_patch_only_title(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Original"})
        tid = r.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"
        assert resp.json()["completed"] is False

    def test_patch_only_completed(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"completed": True})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test"
        assert resp.json()["completed"] is True

    def test_patch_both_fields(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"title": "New", "completed": True})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"
        assert resp.json()["completed"] is True

    def test_patch_no_recognised_fields_422(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"unknown": "field"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "At least one field must be provided"

    def test_patch_only_unknown_fields_422(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"foo": 1, "bar": 2})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "At least one field must be provided"

    def test_patch_title_validation(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        # Blank
        resp = client.patch(f"/todos/{tid}", json={"title": "  "})
        assert resp.status_code == 422
        # Too long
        resp = client.patch(f"/todos/{tid}", json={"title": "a" * 501})
        assert resp.status_code == 422

    def test_patch_title_uniqueness(self, client: TestClient) -> None:
        client.post("/todos", json={"title": "First"})
        r2 = client.post("/todos", json={"title": "Second"})
        tid = r2.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"title": "first"})
        assert resp.status_code == 409

    def test_patch_nonexistent_id_404(self, client: TestClient) -> None:
        resp = client.patch("/todos/9999", json={"title": "Test"})
        assert resp.status_code == 404

    def test_patch_non_integer_id_422(self, client: TestClient) -> None:
        resp = client.patch("/todos/abc", json={"title": "Test"})
        assert resp.status_code == 422

    def test_patch_title_trimmed(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"title": "  Patched  "})
        assert resp.json()["title"] == "Patched"


# ============================================================
# Task 7: Convenience Endpoints
# ============================================================


class TestConvenienceEndpoints:
    def test_complete_sets_true(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.post(f"/todos/{tid}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    def test_incomplete_sets_false(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        client.post(f"/todos/{tid}/complete")
        resp = client.post(f"/todos/{tid}/incomplete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is False

    def test_complete_idempotent(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        client.post(f"/todos/{tid}/complete")
        resp = client.post(f"/todos/{tid}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    def test_incomplete_idempotent(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.post(f"/todos/{tid}/incomplete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is False

    def test_complete_nonexistent_404(self, client: TestClient) -> None:
        resp = client.post("/todos/9999/complete")
        assert resp.status_code == 404

    def test_incomplete_nonexistent_404(self, client: TestClient) -> None:
        resp = client.post("/todos/9999/incomplete")
        assert resp.status_code == 404

    def test_complete_non_integer_422(self, client: TestClient) -> None:
        resp = client.post("/todos/abc/complete")
        assert resp.status_code == 422

    def test_incomplete_non_integer_422(self, client: TestClient) -> None:
        resp = client.post("/todos/abc/incomplete")
        assert resp.status_code == 422


# ============================================================
# Task 8: Delete Todo
# ============================================================


class TestDeleteTodo:
    def test_delete_returns_204(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.delete(f"/todos/{tid}")
        assert resp.status_code == 204
        assert resp.content == b""

    def test_deleted_todo_not_retrievable(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        client.delete(f"/todos/{tid}")
        resp = client.get(f"/todos/{tid}")
        assert resp.status_code == 404

    def test_delete_nonexistent_404(self, client: TestClient) -> None:
        resp = client.delete("/todos/9999")
        assert resp.status_code == 404

    def test_delete_non_integer_422(self, client: TestClient) -> None:
        resp = client.delete("/todos/abc")
        assert resp.status_code == 422

    def test_deleted_id_not_reused(self, client: TestClient) -> None:
        r1 = client.post("/todos", json={"title": "First"})
        id1 = r1.json()["id"]
        client.delete(f"/todos/{id1}")
        r2 = client.post("/todos", json={"title": "Second"})
        id2 = r2.json()["id"]
        assert id2 != id1


# ============================================================
# Task 9: Filtering, Sorting, Search & Pagination
# ============================================================


class TestFilteringSortingPagination:
    def _seed_todos(self, client: TestClient) -> None:
        """Create a set of test todos."""
        todos = [
            "Buy groceries",
            "Clean house",
            "Buy milk",
            "Read book",
            "Write code",
        ]
        for t in todos:
            client.post("/todos", json={"title": t})
        # Mark some as complete
        client.post("/todos/1/complete")
        client.post("/todos/3/complete")

    def test_filter_completed_true(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?completed=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        for item in data["items"]:
            assert item["completed"] is True

    def test_filter_completed_false(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?completed=false")
        data = resp.json()
        for item in data["items"]:
            assert item["completed"] is False

    def test_filter_completed_invalid_422(self, client: TestClient) -> None:
        resp = client.get("/todos?completed=invalid")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "completed must be true or false"

    def test_search_case_insensitive(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?search=buy")
        data = resp.json()
        assert len(data["items"]) == 2
        for item in data["items"]:
            assert "buy" in item["title"].lower()

    def test_search_empty_returns_all(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?search=")
        data = resp.json()
        assert data["total"] == 5

    def test_search_and_filter_combined(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?completed=true&search=buy")
        data = resp.json()
        for item in data["items"]:
            assert item["completed"] is True
            assert "buy" in item["title"].lower()

    def test_sort_title_asc(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?sort=title&order=asc")
        data = resp.json()
        titles = [i["title"].lower() for i in data["items"]]
        assert titles == sorted(titles)

    def test_sort_id_desc_default(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?sort=id&order=desc")
        data = resp.json()
        ids = [i["id"] for i in data["items"]]
        assert ids == sorted(ids, reverse=True)

    def test_sort_invalid_422(self, client: TestClient) -> None:
        resp = client.get("/todos?sort=invalid")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "sort must be 'id' or 'title'"

    def test_order_invalid_422(self, client: TestClient) -> None:
        resp = client.get("/todos?order=invalid")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "order must be 'asc' or 'desc'"

    def test_response_has_pagination_envelope(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?page=1")
        data = resp.json()
        assert "items" in data
        assert "page" in data
        assert "per_page" in data
        assert "total" in data

    def test_pagination_page_2(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?page=2&per_page=1")
        data = resp.json()
        assert data["page"] == 2
        assert data["per_page"] == 1
        assert len(data["items"]) == 1

    def test_page_beyond_total_returns_empty(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?page=999&per_page=10")
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 5

    def test_per_page_1_returns_one(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos?per_page=1")
        data = resp.json()
        assert len(data["items"]) == 1

    def test_page_0_returns_422(self, client: TestClient) -> None:
        resp = client.get("/todos?page=0")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "page must be a positive integer"

    def test_per_page_0_returns_422(self, client: TestClient) -> None:
        resp = client.get("/todos?per_page=0")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"

    def test_per_page_101_returns_422(self, client: TestClient) -> None:
        resp = client.get("/todos?per_page=101")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"

    def test_no_query_params_returns_plain_array(self, client: TestClient) -> None:
        self._seed_todos(client)
        resp = client.get("/todos")
        data = resp.json()
        assert isinstance(data, list)


# ============================================================
# Task 10: Error Handling — Cross-Cutting
# ============================================================


class TestErrorHandling:
    def test_all_errors_have_detail_format(self, client: TestClient) -> None:
        # Missing title
        resp = client.post("/todos", json={})
        data = resp.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_only_one_error_per_request(self, client: TestClient) -> None:
        # Empty body - should only return one error
        resp = client.post("/todos", json={})
        data = resp.json()
        assert isinstance(data["detail"], str)

    def test_validation_order_missing_before_type(self, client: TestClient) -> None:
        # Missing title comes before type check
        resp = client.post("/todos", json={})
        assert resp.json()["detail"] == "title is required"

    def test_title_type_error(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": 123})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be a string"

    def test_completed_type_error(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.put(f"/todos/{tid}", json={"title": "Test", "completed": "yes"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "completed must be a boolean"

    def test_unknown_fields_no_error(self, client: TestClient) -> None:
        resp = client.post("/todos", json={"title": "Test", "extra": "field"})
        assert resp.status_code == 201

    def test_patch_only_unknown_fields_422(self, client: TestClient) -> None:
        r = client.post("/todos", json={"title": "Test"})
        tid = r.json()["id"]
        resp = client.patch(f"/todos/{tid}", json={"unknown": "value"})
        assert resp.status_code == 422


# ============================================================
# Task 12: Integration / End-to-End Tests
# ============================================================


class TestIntegration:
    def test_full_crud_lifecycle(self, client: TestClient) -> None:
        # Create
        r = client.post("/todos", json={"title": "Lifecycle test"})
        assert r.status_code == 201
        tid = r.json()["id"]

        # Retrieve
        r = client.get(f"/todos/{tid}")
        assert r.status_code == 200
        assert r.json()["title"] == "Lifecycle test"

        # Update
        r = client.put(
            f"/todos/{tid}",
            json={"title": "Updated lifecycle", "completed": True},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Updated lifecycle"
        assert r.json()["completed"] is True

        # Delete
        r = client.delete(f"/todos/{tid}")
        assert r.status_code == 204

        # Verify gone
        r = client.get(f"/todos/{tid}")
        assert r.status_code == 404

    def test_multiple_todos_filter_sort_paginate(self, client: TestClient) -> None:
        # Create multiple todos
        titles = ["Apple", "Banana", "Cherry", "Date", "Elderberry"]
        for t in titles:
            client.post("/todos", json={"title": t})

        # Complete some
        client.post("/todos/1/complete")
        client.post("/todos/3/complete")

        # Filter completed
        r = client.get("/todos?completed=true")
        data = r.json()
        assert all(i["completed"] for i in data["items"])

        # Search
        r = client.get("/todos?search=an")
        data = r.json()
        assert all("an" in i["title"].lower() for i in data["items"])

        # Sort by title asc
        r = client.get("/todos?sort=title&order=asc")
        data = r.json()
        t_list = [i["title"].lower() for i in data["items"]]
        assert t_list == sorted(t_list)

        # Paginate
        r = client.get("/todos?page=1&per_page=2")
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2
