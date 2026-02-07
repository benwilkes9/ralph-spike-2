"""Tests for GET /todos query params (Task 9)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def _create_todos(client: AsyncClient) -> None:
    """Create a set of test todos."""
    await client.post("/todos", json={"title": "Buy milk"})
    await client.post("/todos", json={"title": "Walk the dog"})
    await client.post("/todos", json={"title": "Buy eggs"})
    # Mark "Walk the dog" as complete
    resp = await client.get("/todos")
    for todo in resp.json():
        if todo["title"] == "Walk the dog":
            await client.post(f"/todos/{todo['id']}/complete")


async def test_filter_completed_true(client: AsyncClient) -> None:
    """?completed=true returns only completed todos."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"completed": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["completed"] is True for item in data["items"])
    assert len(data["items"]) == 1


async def test_filter_completed_false(client: AsyncClient) -> None:
    """?completed=false returns only incomplete todos."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"completed": "false"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["completed"] is False for item in data["items"])
    assert len(data["items"]) == 2


async def test_filter_completed_invalid(client: AsyncClient) -> None:
    """?completed=invalid returns 422."""
    resp = await client.get("/todos", params={"completed": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


async def test_search_case_insensitive(client: AsyncClient) -> None:
    """?search=buy returns todos with 'buy' in title (case-insensitive)."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"search": "buy"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    titles = [item["title"] for item in data["items"]]
    assert "Buy milk" in titles
    assert "Buy eggs" in titles


async def test_search_empty_returns_all(client: AsyncClient) -> None:
    """Empty search string returns all."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"search": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3


async def test_search_and_filter_combined(client: AsyncClient) -> None:
    """Search + filter combined."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"search": "buy", "completed": "false"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2


async def test_sort_title_asc(client: AsyncClient) -> None:
    """?sort=title&order=asc sorts alphabetically ascending."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"sort": "title", "order": "asc"})
    assert resp.status_code == 200
    data = resp.json()
    titles = [item["title"] for item in data["items"]]
    assert titles == sorted(titles, key=str.lower)


async def test_sort_id_desc_default(client: AsyncClient) -> None:
    """?sort=id&order=desc is default behavior."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"sort": "id", "order": "desc"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert ids == sorted(ids, reverse=True)


async def test_sort_invalid(client: AsyncClient) -> None:
    """Invalid sort value returns 422."""
    resp = await client.get("/todos", params={"sort": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "sort must be 'id' or 'title'"


async def test_order_invalid(client: AsyncClient) -> None:
    """Invalid order value returns 422."""
    resp = await client.get("/todos", params={"order": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "order must be 'asc' or 'desc'"


async def test_paginated_response_shape(client: AsyncClient) -> None:
    """Paginated response includes items, page, per_page, total."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"page": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "page" in data
    assert "per_page" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["total"] == 3


async def test_page_beyond_total(client: AsyncClient) -> None:
    """Page beyond total returns empty items with correct total."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"page": "100"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 3


async def test_per_page_one(client: AsyncClient) -> None:
    """per_page=1 returns one item."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"per_page": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1


async def test_page_zero(client: AsyncClient) -> None:
    """page=0 returns 422."""
    resp = await client.get("/todos", params={"page": "0"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


async def test_per_page_zero(client: AsyncClient) -> None:
    """per_page=0 returns 422."""
    resp = await client.get("/todos", params={"per_page": "0"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


async def test_per_page_over_100(client: AsyncClient) -> None:
    """per_page=101 returns 422."""
    resp = await client.get("/todos", params={"per_page": "101"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


async def test_no_query_params_returns_plain_array(client: AsyncClient) -> None:
    """No query params returns plain JSON array (backward compatible)."""
    await _create_todos(client)
    resp = await client.get("/todos")
    assert resp.status_code == 200
    data: list[dict[str, object]] = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3


async def test_page_non_integer(client: AsyncClient) -> None:
    """page=abc returns 422."""
    resp = await client.get("/todos", params={"page": "abc"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


async def test_page_negative(client: AsyncClient) -> None:
    """page=-1 returns 422."""
    resp = await client.get("/todos", params={"page": "-1"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


async def test_per_page_non_integer(client: AsyncClient) -> None:
    """per_page=abc returns 422."""
    resp = await client.get("/todos", params={"per_page": "abc"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


async def test_sort_title_desc(client: AsyncClient) -> None:
    """?sort=title&order=desc sorts alphabetically descending."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"sort": "title", "order": "desc"})
    assert resp.status_code == 200
    data = resp.json()
    titles = [item["title"] for item in data["items"]]
    assert titles == sorted(titles, key=str.lower, reverse=True)


async def test_sort_id_asc(client: AsyncClient) -> None:
    """?sort=id&order=asc sorts by id ascending (oldest first)."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"sort": "id", "order": "asc"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert ids == sorted(ids)


async def test_pagination_middle_page(client: AsyncClient) -> None:
    """Page 2 returns the correct subset of items."""
    # Create 5 todos (ids 1-5, default order desc: 5,4,3,2,1)
    for i in range(1, 6):
        await client.post("/todos", json={"title": f"Todo {i}"})
    resp = await client.get("/todos", params={"per_page": "2", "page": "2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["per_page"] == 2
    assert len(data["items"]) == 2
    # Default sort is id desc, so page 2 should have ids 3 and 2
    ids = [item["id"] for item in data["items"]]
    assert ids == [3, 2]


async def test_pagination_last_partial_page(client: AsyncClient) -> None:
    """Last page with fewer items than per_page returns remaining items."""
    for i in range(1, 6):
        await client.post("/todos", json={"title": f"Todo {i}"})
    resp = await client.get("/todos", params={"per_page": "2", "page": "3"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == 1


async def test_per_page_max_boundary(client: AsyncClient) -> None:
    """per_page=100 (maximum valid value) succeeds."""
    await _create_todos(client)
    resp = await client.get("/todos", params={"per_page": "100"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_page"] == 100
    assert len(data["items"]) == 3


async def test_combined_search_filter_sort_pagination(client: AsyncClient) -> None:
    """All query params (search + filter + sort + pagination) work together."""
    # Create todos with varying completion status
    await client.post("/todos", json={"title": "Buy apples"})
    await client.post("/todos", json={"title": "Buy bananas"})
    await client.post("/todos", json={"title": "Buy cherries"})
    await client.post("/todos", json={"title": "Sell lemons"})
    # Mark "Buy apples" and "Buy cherries" as complete
    resp = await client.get("/todos")
    for todo in resp.json():
        if todo["title"] in ("Buy apples", "Buy cherries"):
            await client.post(f"/todos/{todo['id']}/complete")
    # Search "buy" + completed=true + sort=title + order=asc + per_page=1 + page=1
    resp = await client.get(
        "/todos",
        params={
            "search": "buy",
            "completed": "true",
            "sort": "title",
            "order": "asc",
            "per_page": "1",
            "page": "1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # Buy apples + Buy cherries
    assert data["per_page"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Buy apples"  # alphabetically first
