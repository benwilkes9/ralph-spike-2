"""Tests for filtering, sorting, and pagination on GET /todos."""

import pytest
from httpx import AsyncClient

# --- Filtering ---


@pytest.mark.asyncio
async def test_filter_completed_true(client: AsyncClient) -> None:
    """GET /todos?completed=true returns only completed todos."""
    r1 = await client.post("/todos", json={"title": "Done"})
    await client.post("/todos", json={"title": "Not done"})
    await client.post(f"/todos/{r1.json()['id']}/complete")
    resp = await client.get("/todos", params={"completed": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    for item in data["items"]:
        assert item["completed"] is True


@pytest.mark.asyncio
async def test_filter_completed_false(client: AsyncClient) -> None:
    """GET /todos?completed=false returns only incomplete todos."""
    r1 = await client.post("/todos", json={"title": "Done"})
    await client.post("/todos", json={"title": "Not done"})
    await client.post(f"/todos/{r1.json()['id']}/complete")
    resp = await client.get("/todos", params={"completed": "false"})
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["completed"] is False


@pytest.mark.asyncio
async def test_filter_completed_invalid_yes(client: AsyncClient) -> None:
    """GET /todos?completed=yes returns 422."""
    resp = await client.get("/todos", params={"completed": "yes"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


@pytest.mark.asyncio
async def test_filter_completed_invalid_1(client: AsyncClient) -> None:
    """GET /todos?completed=1 returns 422."""
    resp = await client.get("/todos", params={"completed": "1"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


@pytest.mark.asyncio
async def test_filter_completed_empty_string(client: AsyncClient) -> None:
    """GET /todos?completed= returns 422."""
    resp = await client.get("/todos", params={"completed": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


# --- Search ---


@pytest.mark.asyncio
async def test_search_case_insensitive(client: AsyncClient) -> None:
    """GET /todos?search=buy returns matching todos case-insensitively."""
    await client.post("/todos", json={"title": "Buy milk"})
    await client.post("/todos", json={"title": "Walk dog"})
    resp = await client.get("/todos", params={"search": "buy"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert "buy" in data["items"][0]["title"].lower()


@pytest.mark.asyncio
async def test_search_uppercase(client: AsyncClient) -> None:
    """GET /todos?search=BUY matches case-insensitively."""
    await client.post("/todos", json={"title": "Buy milk"})
    resp = await client.get("/todos", params={"search": "BUY"})
    data = resp.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_search_no_match(client: AsyncClient) -> None:
    """GET /todos?search=xyz returns empty items."""
    await client.post("/todos", json={"title": "Buy milk"})
    resp = await client.get("/todos", params={"search": "xyz"})
    data = resp.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_search_empty_string(client: AsyncClient) -> None:
    """GET /todos?search= (empty) is treated as no filter."""
    await client.post("/todos", json={"title": "Buy milk"})
    await client.post("/todos", json={"title": "Walk dog"})
    resp = await client.get("/todos", params={"search": ""})
    data = resp.json()
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_search_combined_with_completed(client: AsyncClient) -> None:
    """Search combined with completed filter returns intersection."""
    r1 = await client.post("/todos", json={"title": "Buy milk"})
    await client.post("/todos", json={"title": "Buy bread"})
    await client.post(f"/todos/{r1.json()['id']}/complete")
    resp = await client.get("/todos", params={"search": "buy", "completed": "true"})
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Buy milk"


# --- Sorting ---


@pytest.mark.asyncio
async def test_sort_id_asc(client: AsyncClient) -> None:
    """GET /todos?sort=id&order=asc sorts by ascending id."""
    await client.post("/todos", json={"title": "A"})
    await client.post("/todos", json={"title": "B"})
    resp = await client.get("/todos", params={"sort": "id", "order": "asc"})
    data = resp.json()
    ids = [t["id"] for t in data["items"]]
    assert ids == sorted(ids)


@pytest.mark.asyncio
async def test_sort_id_desc(client: AsyncClient) -> None:
    """GET /todos?sort=id&order=desc sorts by descending id."""
    await client.post("/todos", json={"title": "A"})
    await client.post("/todos", json={"title": "B"})
    resp = await client.get("/todos", params={"sort": "id", "order": "desc"})
    data = resp.json()
    ids = [t["id"] for t in data["items"]]
    assert ids == sorted(ids, reverse=True)


@pytest.mark.asyncio
async def test_sort_title_asc(client: AsyncClient) -> None:
    """GET /todos?sort=title&order=asc sorts alphabetically."""
    await client.post("/todos", json={"title": "Charlie"})
    await client.post("/todos", json={"title": "Alpha"})
    await client.post("/todos", json={"title": "Bravo"})
    resp = await client.get("/todos", params={"sort": "title", "order": "asc"})
    data = resp.json()
    titles = [t["title"] for t in data["items"]]
    assert titles == ["Alpha", "Bravo", "Charlie"]


@pytest.mark.asyncio
async def test_sort_title_desc(client: AsyncClient) -> None:
    """GET /todos?sort=title&order=desc sorts reverse-alphabetically."""
    await client.post("/todos", json={"title": "Charlie"})
    await client.post("/todos", json={"title": "Alpha"})
    await client.post("/todos", json={"title": "Bravo"})
    resp = await client.get("/todos", params={"sort": "title", "order": "desc"})
    data = resp.json()
    titles = [t["title"] for t in data["items"]]
    assert titles == ["Charlie", "Bravo", "Alpha"]


@pytest.mark.asyncio
async def test_sort_invalid(client: AsyncClient) -> None:
    """GET /todos?sort=invalid returns 422."""
    resp = await client.get("/todos", params={"sort": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "sort must be 'id' or 'title'"


@pytest.mark.asyncio
async def test_order_invalid(client: AsyncClient) -> None:
    """GET /todos?order=invalid returns 422."""
    resp = await client.get("/todos", params={"order": "invalid"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "order must be 'asc' or 'desc'"


# --- Pagination ---


@pytest.mark.asyncio
async def test_pagination_basic(client: AsyncClient) -> None:
    """GET /todos?page=1&per_page=2 returns at most 2 items."""
    for i in range(5):
        await client.post("/todos", json={"title": f"Todo {i}"})
    resp = await client.get("/todos", params={"page": "1", "per_page": "2"})
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["per_page"] == 2
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_pagination_per_page_1(client: AsyncClient) -> None:
    """GET /todos?per_page=1 returns exactly 1 item."""
    await client.post("/todos", json={"title": "A"})
    await client.post("/todos", json={"title": "B"})
    resp = await client.get("/todos", params={"per_page": "1"})
    data = resp.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_pagination_beyond_total(client: AsyncClient) -> None:
    """Requesting beyond total pages returns empty items."""
    await client.post("/todos", json={"title": "A"})
    resp = await client.get("/todos", params={"page": "99", "per_page": "10"})
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_page_zero(client: AsyncClient) -> None:
    """GET /todos?page=0 returns 422."""
    resp = await client.get("/todos", params={"page": "0"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


@pytest.mark.asyncio
async def test_page_negative(client: AsyncClient) -> None:
    """GET /todos?page=-1 returns 422."""
    resp = await client.get("/todos", params={"page": "-1"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


@pytest.mark.asyncio
async def test_page_non_numeric(client: AsyncClient) -> None:
    """GET /todos?page=abc returns 422."""
    resp = await client.get("/todos", params={"page": "abc"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


@pytest.mark.asyncio
async def test_per_page_zero(client: AsyncClient) -> None:
    """GET /todos?per_page=0 returns 422."""
    resp = await client.get("/todos", params={"per_page": "0"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


@pytest.mark.asyncio
async def test_per_page_negative(client: AsyncClient) -> None:
    """GET /todos?per_page=-1 returns 422."""
    resp = await client.get("/todos", params={"per_page": "-1"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


@pytest.mark.asyncio
async def test_per_page_over_100(client: AsyncClient) -> None:
    """GET /todos?per_page=101 returns 422."""
    resp = await client.get("/todos", params={"per_page": "101"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


@pytest.mark.asyncio
async def test_per_page_non_numeric(client: AsyncClient) -> None:
    """GET /todos?per_page=abc returns 422."""
    resp = await client.get("/todos", params={"per_page": "abc"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


# --- Response envelope logic ---


@pytest.mark.asyncio
async def test_no_params_returns_plain_array(client: AsyncClient) -> None:
    """GET /todos with no query params returns a plain JSON array."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.get("/todos")
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_page_param_returns_envelope(client: AsyncClient) -> None:
    """GET /todos?page=1 returns the envelope format."""
    resp = await client.get("/todos", params={"page": "1"})
    data = resp.json()
    assert "items" in data
    assert "page" in data
    assert "per_page" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_completed_param_returns_envelope(client: AsyncClient) -> None:
    """GET /todos?completed=false returns the envelope format."""
    resp = await client.get("/todos", params={"completed": "false"})
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_search_param_returns_envelope(client: AsyncClient) -> None:
    """GET /todos?search= returns envelope (param present, even if empty)."""
    resp = await client.get("/todos", params={"search": ""})
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_sort_param_returns_envelope(client: AsyncClient) -> None:
    """GET /todos?sort=title returns the envelope format."""
    resp = await client.get("/todos", params={"sort": "title"})
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_order_param_returns_envelope(client: AsyncClient) -> None:
    """GET /todos?order=asc returns the envelope format."""
    resp = await client.get("/todos", params={"order": "asc"})
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_envelope_total_reflects_filtered(client: AsyncClient) -> None:
    """The total field reflects matching items before pagination."""
    for i in range(5):
        await client.post("/todos", json={"title": f"Todo {i}"})
    resp = await client.get("/todos", params={"page": "1", "per_page": "2"})
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["per_page"] == 2


@pytest.mark.asyncio
async def test_per_page_100_accepted(client: AsyncClient) -> None:
    """GET /todos?per_page=100 is accepted (upper boundary)."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.get("/todos", params={"per_page": "100"})
    assert resp.status_code == 200
    assert resp.json()["per_page"] == 100


@pytest.mark.asyncio
async def test_pagination_empty_database(client: AsyncClient) -> None:
    """Paginated request on empty database returns empty items with total 0."""
    resp = await client.get("/todos", params={"page": "1", "per_page": "10"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 10


@pytest.mark.asyncio
async def test_page_float_string(client: AsyncClient) -> None:
    """GET /todos?page=1.5 returns 422."""
    resp = await client.get("/todos", params={"page": "1.5"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


@pytest.mark.asyncio
async def test_per_page_float_string(client: AsyncClient) -> None:
    """GET /todos?per_page=1.5 returns 422."""
    resp = await client.get("/todos", params={"per_page": "1.5"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "per_page must be an integer between 1 and 100"


# --- Case-insensitive title sorting ---


@pytest.mark.asyncio
async def test_sort_title_asc_case_insensitive(client: AsyncClient) -> None:
    """sort=title&order=asc sorts case-insensitively (e.g. 'apple' before 'Banana')."""
    await client.post("/todos", json={"title": "banana"})
    await client.post("/todos", json={"title": "Apple"})
    await client.post("/todos", json={"title": "cherry"})
    resp = await client.get("/todos", params={"sort": "title", "order": "asc"})
    data = resp.json()
    titles = [t["title"] for t in data["items"]]
    assert titles == ["Apple", "banana", "cherry"]


@pytest.mark.asyncio
async def test_sort_title_desc_case_insensitive(client: AsyncClient) -> None:
    """sort=title&order=desc sorts case-insensitively in reverse."""
    await client.post("/todos", json={"title": "banana"})
    await client.post("/todos", json={"title": "Apple"})
    await client.post("/todos", json={"title": "cherry"})
    resp = await client.get("/todos", params={"sort": "title", "order": "desc"})
    data = resp.json()
    titles = [t["title"] for t in data["items"]]
    assert titles == ["cherry", "banana", "Apple"]


# --- Default sort order in paginated responses ---


@pytest.mark.asyncio
async def test_paginated_default_sort_id_desc(client: AsyncClient) -> None:
    """Paginated response defaults to id descending when sort/order omitted."""
    await client.post("/todos", json={"title": "First"})
    await client.post("/todos", json={"title": "Second"})
    await client.post("/todos", json={"title": "Third"})
    resp = await client.get("/todos", params={"page": "1", "per_page": "10"})
    data = resp.json()
    ids = [t["id"] for t in data["items"]]
    assert ids == sorted(ids, reverse=True)


# --- Pagination page 2+ ---


@pytest.mark.asyncio
async def test_pagination_page_2(client: AsyncClient) -> None:
    """Page 2 returns a different, correct set of items."""
    for i in range(5):
        await client.post("/todos", json={"title": f"Todo {i}"})
    resp1 = await client.get(
        "/todos", params={"page": "1", "per_page": "2", "sort": "id", "order": "asc"}
    )
    resp2 = await client.get(
        "/todos", params={"page": "2", "per_page": "2", "sort": "id", "order": "asc"}
    )
    page1_ids = [t["id"] for t in resp1.json()["items"]]
    page2_ids = [t["id"] for t in resp2.json()["items"]]
    assert len(page1_ids) == 2
    assert len(page2_ids) == 2
    # No overlap and page 2 comes after page 1
    assert set(page1_ids).isdisjoint(set(page2_ids))
    assert min(page2_ids) > max(page1_ids)


# --- Paginated response echoes requested page ---


@pytest.mark.asyncio
async def test_pagination_beyond_total_echoes_page(client: AsyncClient) -> None:
    """Response echoes back the requested page number even beyond total."""
    await client.post("/todos", json={"title": "A"})
    resp = await client.get("/todos", params={"page": "99", "per_page": "10"})
    data = resp.json()
    assert data["page"] == 99
    assert data["items"] == []
    assert data["total"] == 1


# --- Search with LIKE wildcards ---


@pytest.mark.asyncio
async def test_search_with_percent_wildcard(client: AsyncClient) -> None:
    """Search containing % is treated as literal, not LIKE wildcard."""
    await client.post("/todos", json={"title": "100% complete"})
    await client.post("/todos", json={"title": "Unrelated"})
    resp = await client.get("/todos", params={"search": "100%"})
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "100% complete"


@pytest.mark.asyncio
async def test_search_with_underscore_wildcard(client: AsyncClient) -> None:
    """Search containing _ is treated as literal, not LIKE wildcard."""
    await client.post("/todos", json={"title": "my_task"})
    await client.post("/todos", json={"title": "myXtask"})
    resp = await client.get("/todos", params={"search": "my_task"})
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "my_task"


# --- Create with non-boolean completed ---


@pytest.mark.asyncio
async def test_create_completed_non_boolean_ignored(client: AsyncClient) -> None:
    """POST with completed: 'yes' still succeeds (completed not accepted on create)."""
    resp = await client.post(
        "/todos", json={"title": "Test ignored", "completed": "yes"}
    )
    assert resp.status_code == 201
    assert resp.json()["completed"] is False


# --- Search with backslash ---


@pytest.mark.asyncio
async def test_search_with_backslash(client: AsyncClient) -> None:
    r"""Search containing \ is treated as literal, not LIKE escape."""
    await client.post("/todos", json={"title": r"c:\users\docs"})
    await client.post("/todos", json={"title": "unrelated"})
    resp = await client.get("/todos", params={"search": r"c:\users"})
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == r"c:\users\docs"


# --- sort=title alone defaults to desc ---


@pytest.mark.asyncio
async def test_sort_title_default_order_desc(client: AsyncClient) -> None:
    """sort=title without order defaults to descending."""
    await client.post("/todos", json={"title": "Alpha"})
    await client.post("/todos", json={"title": "Charlie"})
    await client.post("/todos", json={"title": "Bravo"})
    resp = await client.get("/todos", params={"sort": "title"})
    data = resp.json()
    titles = [t["title"] for t in data["items"]]
    assert titles == ["Charlie", "Bravo", "Alpha"]


# --- order=asc alone defaults to sort by id ---


@pytest.mark.asyncio
async def test_order_asc_default_sort_id(client: AsyncClient) -> None:
    """order=asc without sort defaults to id ascending."""
    await client.post("/todos", json={"title": "First"})
    await client.post("/todos", json={"title": "Second"})
    await client.post("/todos", json={"title": "Third"})
    resp = await client.get("/todos", params={"order": "asc"})
    data = resp.json()
    ids = [t["id"] for t in data["items"]]
    assert ids == sorted(ids)


# --- Combined filtering + sorting + pagination ---


@pytest.mark.asyncio
async def test_combined_filter_sort_paginate(client: AsyncClient) -> None:
    """All features combined: search + completed + sort + pagination."""
    r1 = await client.post("/todos", json={"title": "Buy apples"})
    await client.post("/todos", json={"title": "Buy bananas"})
    r3 = await client.post("/todos", json={"title": "Buy cherries"})
    await client.post("/todos", json={"title": "Walk dog"})
    await client.post(f"/todos/{r1.json()['id']}/complete")
    await client.post(f"/todos/{r3.json()['id']}/complete")
    resp = await client.get(
        "/todos",
        params={
            "search": "buy",
            "completed": "true",
            "sort": "title",
            "order": "asc",
            "page": "1",
            "per_page": "1",
        },
    )
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Buy apples"


# --- Delete then delete again ---


@pytest.mark.asyncio
async def test_delete_twice_returns_404(client: AsyncClient) -> None:
    """DELETE same id twice: first 204, second 404."""
    r = await client.post("/todos", json={"title": "Delete twice"})
    todo_id = r.json()["id"]
    resp1 = await client.delete(f"/todos/{todo_id}")
    assert resp1.status_code == 204
    resp2 = await client.delete(f"/todos/{todo_id}")
    assert resp2.status_code == 404


# --- Interior whitespace preserved ---


@pytest.mark.asyncio
async def test_title_interior_whitespace_preserved(
    client: AsyncClient,
) -> None:
    """Interior whitespace in title is preserved after trim."""
    resp = await client.post("/todos", json={"title": "  hello   world  "})
    assert resp.status_code == 201
    assert resp.json()["title"] == "hello   world"


# --- completed filter case sensitivity ---


@pytest.mark.asyncio
async def test_filter_completed_uppercase_true(client: AsyncClient) -> None:
    """GET /todos?completed=TRUE returns 422 (case-sensitive)."""
    resp = await client.get("/todos", params={"completed": "TRUE"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


@pytest.mark.asyncio
async def test_filter_completed_title_case(client: AsyncClient) -> None:
    """GET /todos?completed=True returns 422 (case-sensitive)."""
    resp = await client.get("/todos", params={"completed": "True"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


@pytest.mark.asyncio
async def test_filter_completed_zero(client: AsyncClient) -> None:
    """GET /todos?completed=0 returns 422."""
    resp = await client.get("/todos", params={"completed": "0"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


# --- sort/order case sensitivity ---


@pytest.mark.asyncio
async def test_sort_uppercase_invalid(client: AsyncClient) -> None:
    """GET /todos?sort=ID returns 422 (case-sensitive)."""
    resp = await client.get("/todos", params={"sort": "ID"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "sort must be 'id' or 'title'"


@pytest.mark.asyncio
async def test_order_uppercase_invalid(client: AsyncClient) -> None:
    """GET /todos?order=ASC returns 422 (case-sensitive)."""
    resp = await client.get("/todos", params={"order": "ASC"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "order must be 'asc' or 'desc'"


# --- Envelope total reflects filtered count ---


@pytest.mark.asyncio
async def test_envelope_total_with_completed_filter(
    client: AsyncClient,
) -> None:
    """Envelope total reflects filtered count, not total DB count."""
    r1 = await client.post("/todos", json={"title": "A"})
    await client.post("/todos", json={"title": "B"})
    await client.post("/todos", json={"title": "C"})
    await client.post(f"/todos/{r1.json()['id']}/complete")
    resp = await client.get("/todos", params={"completed": "true", "page": "1"})
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_envelope_total_with_search_filter(
    client: AsyncClient,
) -> None:
    """Envelope total reflects search-filtered count."""
    await client.post("/todos", json={"title": "Buy milk"})
    await client.post("/todos", json={"title": "Walk dog"})
    await client.post("/todos", json={"title": "Buy bread"})
    resp = await client.get("/todos", params={"search": "buy", "page": "1"})
    data = resp.json()
    assert data["total"] == 2


# --- Default page and per_page ---


@pytest.mark.asyncio
async def test_default_per_page_is_10(client: AsyncClient) -> None:
    """When only page param given, per_page defaults to 10."""
    for i in range(12):
        await client.post("/todos", json={"title": f"Item {i}"})
    resp = await client.get("/todos", params={"page": "1"})
    data = resp.json()
    assert data["per_page"] == 10
    assert len(data["items"]) == 10
    assert data["total"] == 12


@pytest.mark.asyncio
async def test_default_page_is_1(client: AsyncClient) -> None:
    """When only per_page param given, page defaults to 1."""
    for i in range(3):
        await client.post("/todos", json={"title": f"Item {i}"})
    resp = await client.get("/todos", params={"per_page": "2"})
    data = resp.json()
    assert data["page"] == 1
    assert len(data["items"]) == 2


# --- Last partial page ---


@pytest.mark.asyncio
async def test_pagination_last_partial_page(client: AsyncClient) -> None:
    """Last page with fewer items than per_page returns correct count."""
    for i in range(5):
        await client.post("/todos", json={"title": f"Item {i}"})
    resp = await client.get(
        "/todos",
        params={"page": "2", "per_page": "3", "sort": "id", "order": "asc"},
    )
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 2


# --- Search combined with sort ---


@pytest.mark.asyncio
async def test_search_combined_with_sort(client: AsyncClient) -> None:
    """Search and sort can be combined."""
    await client.post("/todos", json={"title": "Buy bananas"})
    await client.post("/todos", json={"title": "Buy apples"})
    await client.post("/todos", json={"title": "Walk dog"})
    resp = await client.get(
        "/todos",
        params={"search": "buy", "sort": "title", "order": "asc"},
    )
    data = resp.json()
    assert len(data["items"]) == 2
    titles = [t["title"] for t in data["items"]]
    assert titles == ["Buy apples", "Buy bananas"]


# --- Search combined with pagination ---


@pytest.mark.asyncio
async def test_search_combined_with_pagination(
    client: AsyncClient,
) -> None:
    """Search with pagination returns correct page of results."""
    await client.post("/todos", json={"title": "Buy apples"})
    await client.post("/todos", json={"title": "Buy bananas"})
    await client.post("/todos", json={"title": "Buy cherries"})
    await client.post("/todos", json={"title": "Walk dog"})
    resp = await client.get(
        "/todos",
        params={
            "search": "buy",
            "page": "1",
            "per_page": "2",
            "sort": "id",
            "order": "asc",
        },
    )
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


# --- completed filter combined with sort ---


@pytest.mark.asyncio
async def test_completed_filter_with_sort(client: AsyncClient) -> None:
    """Completed filter combined with sort works correctly."""
    r1 = await client.post("/todos", json={"title": "Charlie"})
    r2 = await client.post("/todos", json={"title": "Alpha"})
    await client.post("/todos", json={"title": "Bravo"})
    await client.post(f"/todos/{r1.json()['id']}/complete")
    await client.post(f"/todos/{r2.json()['id']}/complete")
    resp = await client.get(
        "/todos",
        params={
            "completed": "true",
            "sort": "title",
            "order": "asc",
        },
    )
    data = resp.json()
    titles = [t["title"] for t in data["items"]]
    assert titles == ["Alpha", "Charlie"]


# --- completed filter combined with pagination ---


@pytest.mark.asyncio
async def test_completed_filter_with_pagination(
    client: AsyncClient,
) -> None:
    """Completed filter with pagination returns correct results."""
    for i in range(5):
        r = await client.post("/todos", json={"title": f"Task {i}"})
        if i % 2 == 0:
            await client.post(f"/todos/{r.json()['id']}/complete")
    resp = await client.get(
        "/todos",
        params={"completed": "true", "page": "1", "per_page": "2"},
    )
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["completed"] is True


# --- Paginated list item shape ---


@pytest.mark.asyncio
async def test_paginated_list_item_shape(client: AsyncClient) -> None:
    """Paginated list items have exactly {id, title, completed}."""
    await client.post("/todos", json={"title": "Test"})
    resp = await client.get("/todos", params={"page": "1"})
    data = resp.json()
    for item in data["items"]:
        assert set(item.keys()) == {"id", "title", "completed"}


# --- Empty string query parameter edge cases ---


@pytest.mark.asyncio
async def test_sort_empty_string(client: AsyncClient) -> None:
    """GET /todos?sort= (empty) returns 422."""
    resp = await client.get("/todos", params={"sort": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "sort must be 'id' or 'title'"


@pytest.mark.asyncio
async def test_order_empty_string(client: AsyncClient) -> None:
    """GET /todos?order= (empty) returns 422."""
    resp = await client.get("/todos", params={"order": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "order must be 'asc' or 'desc'"


@pytest.mark.asyncio
async def test_page_empty_string(client: AsyncClient) -> None:
    """GET /todos?page= (empty) returns 422."""
    resp = await client.get("/todos", params={"page": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "page must be a positive integer"


@pytest.mark.asyncio
async def test_per_page_empty_string(client: AsyncClient) -> None:
    """GET /todos?per_page= (empty) returns 422."""
    resp = await client.get("/todos", params={"per_page": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == ("per_page must be an integer between 1 and 100")


# --- Substring match in the middle of a title ---


@pytest.mark.asyncio
async def test_search_substring_middle(client: AsyncClient) -> None:
    """Search matches substring in the middle of a title."""
    await client.post("/todos", json={"title": "Buy milk please"})
    await client.post("/todos", json={"title": "Walk dog"})
    resp = await client.get("/todos", params={"search": "milk"})
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Buy milk please"


# --- completed filter additional case sensitivity ---


@pytest.mark.asyncio
async def test_filter_completed_false_uppercase(
    client: AsyncClient,
) -> None:
    """GET /todos?completed=FALSE returns 422 (case-sensitive)."""
    resp = await client.get("/todos", params={"completed": "FALSE"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"


@pytest.mark.asyncio
async def test_filter_completed_false_title_case(
    client: AsyncClient,
) -> None:
    """GET /todos?completed=False returns 422 (case-sensitive)."""
    resp = await client.get("/todos", params={"completed": "False"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "completed must be true or false"
