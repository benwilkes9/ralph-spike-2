"""Tests for GET /todos filtering, sorting, search, and pagination."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helper to seed data
# ---------------------------------------------------------------------------


async def _seed_todos(client: AsyncClient) -> list[dict[str, object]]:
    """Create a set of test todos and return them in creation order.

    Creates:
      1. "Buy milk"       (completed=False)
      2. "Buy eggs"       (completed=False)
      3. "Clean house"    (completed=True via /complete)
      4. "Walk dog"       (completed=True via /complete)
      5. "Read book"      (completed=False)
    """
    titles = ["Buy milk", "Buy eggs", "Clean house", "Walk dog", "Read book"]
    todos: list[dict[str, object]] = []
    for title in titles:
        resp = await client.post("/todos", json={"title": title})
        assert resp.status_code == 201
        todos.append(resp.json())

    # Mark some as complete
    await client.post(f"/todos/{todos[2]['id']}/complete")  # Clean house
    await client.post(f"/todos/{todos[3]['id']}/complete")  # Walk dog

    return todos


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


async def test_filter_completed_true(client: AsyncClient) -> None:
    """?completed=true returns only completed todos."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"completed": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert all(item["completed"] is True for item in data["items"])
    assert data["total"] == 2


async def test_filter_completed_false(client: AsyncClient) -> None:
    """?completed=false returns only incomplete todos."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"completed": "false"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert all(item["completed"] is False for item in data["items"])
    assert data["total"] == 3


async def test_filter_completed_invalid(client: AsyncClient) -> None:
    """?completed=invalid returns 422."""
    resp = await client.get("/todos", params={"completed": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def test_search_case_insensitive_lower(client: AsyncClient) -> None:
    """?search=buy returns todos with 'buy' in title (case-insensitive)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"search": "buy"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    titles = [item["title"] for item in data["items"]]
    assert "Buy milk" in titles
    assert "Buy eggs" in titles


async def test_search_case_insensitive_upper(client: AsyncClient) -> None:
    """?search=BUY also matches 'Buy milk' (case-insensitive)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"search": "BUY"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


async def test_search_empty_string(client: AsyncClient) -> None:
    """?search= (empty) returns all todos (no filter applied)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"search": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5


async def test_search_no_matches(client: AsyncClient) -> None:
    """?search=xyz with no matches returns empty items with total: 0."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"search": "xyz"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


async def test_sort_id_desc(client: AsyncClient) -> None:
    """?sort=id&order=desc returns newest first (default behaviour)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"sort": "id", "order": "desc"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert ids == sorted(ids, reverse=True)


async def test_sort_id_asc(client: AsyncClient) -> None:
    """?sort=id&order=asc returns oldest first."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"sort": "id", "order": "asc"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert ids == sorted(ids)


async def test_sort_title_asc(client: AsyncClient) -> None:
    """?sort=title&order=asc returns alphabetical ascending (case-insensitive)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"sort": "title", "order": "asc"})
    assert resp.status_code == 200
    data = resp.json()
    titles = [item["title"] for item in data["items"]]
    assert titles == sorted(titles, key=str.lower)


async def test_sort_title_desc(client: AsyncClient) -> None:
    """?sort=title&order=desc returns reverse alphabetical (case-insensitive)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"sort": "title", "order": "desc"})
    assert resp.status_code == 200
    data = resp.json()
    titles = [item["title"] for item in data["items"]]
    assert titles == sorted(titles, key=str.lower, reverse=True)


async def test_sort_invalid(client: AsyncClient) -> None:
    """?sort=invalid returns 422."""
    resp = await client.get("/todos", params={"sort": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "sort must be 'id' or 'title'"


async def test_order_invalid(client: AsyncClient) -> None:
    """?order=invalid returns 422."""
    resp = await client.get("/todos", params={"order": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "order must be 'asc' or 'desc'"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


async def test_pagination_page1_per_page2(client: AsyncClient) -> None:
    """?page=1&per_page=2 with 5 todos returns 2 items, total: 5."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"page": "1", "per_page": "2"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["per_page"] == 2


async def test_pagination_last_page(client: AsyncClient) -> None:
    """?page=3&per_page=2 with 5 todos returns 1 item (last page)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"page": "3", "per_page": "2"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 5


async def test_pagination_beyond_last_page(client: AsyncClient) -> None:
    """?page=100&per_page=10 with 5 todos returns empty items, total: 5."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"page": "100", "per_page": "10"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 5


async def test_pagination_per_page_1(client: AsyncClient) -> None:
    """?per_page=1 returns exactly 1 item per page."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"per_page": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1


async def test_pagination_per_page_100(client: AsyncClient) -> None:
    """?per_page=100 works (max boundary)."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"per_page": "100"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 5
    assert data["per_page"] == 100


async def test_pagination_page_zero(client: AsyncClient) -> None:
    """?page=0 returns 422."""
    resp = await client.get("/todos", params={"page": "0"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


async def test_pagination_page_negative(client: AsyncClient) -> None:
    """?page=-1 returns 422."""
    resp = await client.get("/todos", params={"page": "-1"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


async def test_pagination_page_abc(client: AsyncClient) -> None:
    """?page=abc returns 422."""
    resp = await client.get("/todos", params={"page": "abc"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


async def test_pagination_per_page_zero(client: AsyncClient) -> None:
    """?per_page=0 returns 422."""
    resp = await client.get("/todos", params={"per_page": "0"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


async def test_pagination_per_page_101(client: AsyncClient) -> None:
    """?per_page=101 returns 422."""
    resp = await client.get("/todos", params={"per_page": "101"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


async def test_pagination_per_page_abc(client: AsyncClient) -> None:
    """?per_page=abc returns 422."""
    resp = await client.get("/todos", params={"per_page": "abc"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------


async def test_combined_completed_and_search(client: AsyncClient) -> None:
    """?completed=true&search=clean returns only completed todos containing 'clean'."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"completed": "true", "search": "clean"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Clean house"
    assert data["items"][0]["completed"] is True


async def test_combined_all_params(client: AsyncClient) -> None:
    """?completed=false&sort=title&order=asc&page=1&per_page=5 combines all."""
    await _seed_todos(client)
    resp = await client.get(
        "/todos",
        params={
            "completed": "false",
            "sort": "title",
            "order": "asc",
            "page": "1",
            "per_page": "5",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    # Should be sorted alphabetically: Buy eggs, Buy milk, Read book
    titles = [item["title"] for item in data["items"]]
    assert titles == sorted(titles, key=str.lower)
    assert all(item["completed"] is False for item in data["items"])


async def test_search_pagination_total_reflects_filtered_count(
    client: AsyncClient,
) -> None:
    """Search + pagination: total reflects filtered count, not total database count."""
    await _seed_todos(client)
    resp = await client.get(
        "/todos", params={"search": "buy", "page": "1", "per_page": "1"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # Only 2 "buy" todos, not 5 total
    assert len(data["items"]) == 1


# ---------------------------------------------------------------------------
# Envelope vs. array
# ---------------------------------------------------------------------------


async def test_no_params_returns_plain_array(client: AsyncClient) -> None:
    """No query params at all: response is a plain JSON array."""
    await _seed_todos(client)
    resp = await client.get("/todos")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_any_param_returns_envelope(client: AsyncClient) -> None:
    """Any single query param present: response is an envelope object."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"sort": "id"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert "page" in data
    assert "per_page" in data
    assert "total" in data


async def test_empty_search_param_returns_envelope(
    client: AsyncClient,
) -> None:
    """?search= (empty search, but param is present): response is an envelope."""
    await _seed_todos(client)
    resp = await client.get("/todos", params={"search": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert data["total"] == 5
