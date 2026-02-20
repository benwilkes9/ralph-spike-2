"""Tests for Task 9: List Filtering, Sorting, Search & Pagination."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.testclient import TestClient

_PER_PAGE_ERR = "per_page must be an integer between 1 and 100"


def _create_todo(
    client: TestClient, title: str = "Test todo", completed: bool = False
) -> dict[str, Any]:
    """Helper to create a todo and optionally mark it completed."""
    resp = client.post("/todos", json={"title": title})
    assert resp.status_code == 201
    todo = resp.json()
    if completed:
        resp = client.post(f"/todos/{todo['id']}/complete")
        assert resp.status_code == 200
        todo = resp.json()
    return todo


def _seed_todos(client: TestClient) -> list[dict[str, Any]]:
    """Create a standard set of todos for testing."""
    todos: list[dict[str, Any]] = [
        _create_todo(client, "Buy milk", completed=True),
        _create_todo(client, "Buy eggs", completed=False),
        _create_todo(client, "Walk the dog", completed=True),
        _create_todo(client, "Read a book", completed=False),
        _create_todo(client, "Buy bread", completed=False),
    ]
    return todos


class TestBackwardCompatibility:
    """GET /todos with no params returns plain JSON array."""

    def test_no_params_returns_plain_array(
        self, client: TestClient
    ) -> None:
        """No params returns plain JSON array (backward compatible)."""
        _create_todo(client, "First")
        _create_todo(client, "Second")
        resp = client.get("/todos")
        assert resp.status_code == 200
        data: list[Any] = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2


class TestCompletedFilter:
    """GET /todos?completed=... filtering tests."""

    def test_completed_true(self, client: TestClient) -> None:
        """Returns only completed todos in paginated envelope."""
        _seed_todos(client)
        resp = client.get("/todos?completed=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 2
        for item in data["items"]:
            assert item["completed"] is True

    def test_completed_false(self, client: TestClient) -> None:
        """Returns only incomplete todos in paginated envelope."""
        _seed_todos(client)
        resp = client.get("/todos?completed=false")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] == 3
        for item in data["items"]:
            assert item["completed"] is False

    def test_completed_invalid(self, client: TestClient) -> None:
        """GET /todos?completed=maybe returns 422."""
        resp = client.get("/todos?completed=maybe")
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "completed must be true or false",
        }

    def test_completed_true_total_reflects_filter(
        self, client: TestClient
    ) -> None:
        """Total reflects only matching (completed) todos."""
        _seed_todos(client)
        resp = client.get("/todos?completed=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2  # only 2 completed out of 5


class TestSearchFilter:
    """GET /todos?search=... tests."""

    def test_search_case_insensitive(self, client: TestClient) -> None:
        """Search is case-insensitive substring match on title."""
        _seed_todos(client)
        resp = client.get("/todos?search=buy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        titles = [item["title"] for item in data["items"]]
        for title in titles:
            assert "buy" in title.lower()

    def test_search_empty_string(self, client: TestClient) -> None:
        """Empty search returns all todos in paginated envelope."""
        _seed_todos(client)
        resp = client.get("/todos?search=")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] == 5

    def test_search_combined_with_completed(
        self, client: TestClient
    ) -> None:
        """Completed filter and search can be combined."""
        _seed_todos(client)
        resp = client.get("/todos?completed=true&search=buy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Buy milk"
        assert data["items"][0]["completed"] is True


class TestSorting:
    """GET /todos?sort=...&order=... tests."""

    def test_sort_title_asc(self, client: TestClient) -> None:
        """Sorts alphabetically ascending by title."""
        _seed_todos(client)
        resp = client.get("/todos?sort=title&order=asc")
        assert resp.status_code == 200
        data = resp.json()
        titles = [item["title"] for item in data["items"]]
        assert titles == sorted(titles, key=str.lower)

    def test_sort_id_desc(self, client: TestClient) -> None:
        """Sorts by id descending."""
        _seed_todos(client)
        resp = client.get("/todos?sort=id&order=desc")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data["items"]]
        assert ids == sorted(ids, reverse=True)

    def test_sort_invalid(self, client: TestClient) -> None:
        """GET /todos?sort=invalid returns 422."""
        resp = client.get("/todos?sort=invalid")
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "sort must be 'id' or 'title'",
        }

    def test_order_invalid(self, client: TestClient) -> None:
        """GET /todos?order=invalid returns 422."""
        resp = client.get("/todos?order=invalid")
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "order must be 'asc' or 'desc'",
        }


class TestPagination:
    """GET /todos?page=...&per_page=... tests."""

    def test_page_and_per_page(self, client: TestClient) -> None:
        """page=1&per_page=2 with 5 todos returns 2 items."""
        _seed_todos(client)
        resp = client.get("/todos?page=1&per_page=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2

    def test_page_beyond_last(self, client: TestClient) -> None:
        """page=100 returns empty items with correct total."""
        _seed_todos(client)
        resp = client.get("/todos?page=100")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 5
        assert data["page"] == 100

    def test_page_zero(self, client: TestClient) -> None:
        """GET /todos?page=0 returns 422."""
        resp = client.get("/todos?page=0")
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "page must be a positive integer",
        }

    def test_page_abc(self, client: TestClient) -> None:
        """GET /todos?page=abc returns 422."""
        resp = client.get("/todos?page=abc")
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "page must be a positive integer",
        }

    def test_per_page_zero(self, client: TestClient) -> None:
        """GET /todos?per_page=0 returns 422."""
        resp = client.get("/todos?per_page=0")
        assert resp.status_code == 422
        assert resp.json() == {"detail": _PER_PAGE_ERR}

    def test_per_page_101(self, client: TestClient) -> None:
        """GET /todos?per_page=101 returns 422."""
        resp = client.get("/todos?per_page=101")
        assert resp.status_code == 422
        assert resp.json() == {"detail": _PER_PAGE_ERR}

    def test_per_page_1(self, client: TestClient) -> None:
        """GET /todos?per_page=1 returns one item per page."""
        _seed_todos(client)
        resp = client.get("/todos?per_page=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 5

    def test_per_page_abc(self, client: TestClient) -> None:
        """GET /todos?per_page=abc (non-integer) returns 422."""
        resp = client.get("/todos?per_page=abc")
        assert resp.status_code == 422
        assert resp.json() == {"detail": _PER_PAGE_ERR}

    def test_page_negative(self, client: TestClient) -> None:
        """GET /todos?page=-1 returns 422."""
        resp = client.get("/todos?page=-1")
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "page must be a positive integer",
        }


class TestDefaultBehaviorWithParams:
    """Default sorting and pagination when query params are present."""

    def test_completed_false_default_sort(
        self, client: TestClient
    ) -> None:
        """completed=false uses default sort id descending."""
        _seed_todos(client)
        resp = client.get("/todos?completed=false")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data["items"]]
        assert ids == sorted(ids, reverse=True)

    def test_default_pagination_with_params(
        self, client: TestClient
    ) -> None:
        """Default pagination: page=1, per_page=10."""
        _seed_todos(client)
        resp = client.get("/todos?completed=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
