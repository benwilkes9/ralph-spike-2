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
