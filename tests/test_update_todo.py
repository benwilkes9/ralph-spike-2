"""Tests for update todo endpoints: PUT, PATCH, complete, incomplete."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helper: create a todo via POST for test setup
# ---------------------------------------------------------------------------
async def _create_todo(client: AsyncClient, title: str) -> dict[str, object]:
    resp = await client.post("/todos", json={"title": title})
    assert resp.status_code == 201
    data: dict[str, object] = resp.json()
    return data


# ===========================================================================
# PUT /todos/{id}
# ===========================================================================


class TestPutTodo:
    """Full replacement via PUT /todos/{id}."""

    async def test_put_updates_title_resets_completed(
        self, client: AsyncClient
    ) -> None:
        todo = await _create_todo(client, "Original")
        resp = await client.put(f"/todos/{todo['id']}", json={"title": "Updated"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated"
        assert data["completed"] is False  # reset to default

    async def test_put_with_completed_true(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Put completed")
        resp = await client.put(
            f"/todos/{todo['id']}",
            json={"title": "Put completed v2", "completed": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Put completed v2"
        assert data["completed"] is True

    async def test_put_missing_title_returns_422(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Missing title put")
        resp = await client.put(f"/todos/{todo['id']}", json={})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title is required"

    async def test_put_blank_title_returns_422(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Blank title put")
        resp = await client.put(f"/todos/{todo['id']}", json={"title": ""})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must not be blank"

    async def test_put_title_too_long_returns_422(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Long title put")
        resp = await client.put(f"/todos/{todo['id']}", json={"title": "a" * 501})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "title must be 500 characters or fewer"

    async def test_put_duplicate_title_different_todo_returns_409(
        self, client: AsyncClient
    ) -> None:
        await _create_todo(client, "Existing title")
        todo2 = await _create_todo(client, "Another title")
        resp = await client.put(
            f"/todos/{todo2['id']}", json={"title": "existing title"}
        )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "A todo with this title already exists"

    async def test_put_same_title_as_self_succeeds(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Buy Milk")
        resp = await client.put(f"/todos/{todo['id']}", json={"title": "buy milk"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "buy milk"

    async def test_put_nonexistent_id_returns_404(self, client: AsyncClient) -> None:
        resp = await client.put("/todos/99999", json={"title": "No exist"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    async def test_put_non_integer_id_returns_422(self, client: AsyncClient) -> None:
        resp = await client.put("/todos/abc", json={"title": "Bad id"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    async def test_put_trims_title(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Trim put")
        resp = await client.put(f"/todos/{todo['id']}", json={"title": "  Updated  "})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    async def test_put_completed_invalid_type_returns_422(
        self, client: AsyncClient
    ) -> None:
        todo = await _create_todo(client, "Type error put")
        resp = await client.put(
            f"/todos/{todo['id']}",
            json={"title": "Valid", "completed": "yes"},
        )
        assert resp.status_code == 422


# ===========================================================================
# PATCH /todos/{id}
# ===========================================================================


class TestPatchTodo:
    """Partial update via PATCH /todos/{id}."""

    async def test_patch_title_only(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Patch title only")
        resp = await client.patch(f"/todos/{todo['id']}", json={"title": "New Title"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New Title"
        assert data["completed"] is False  # unchanged

    async def test_patch_completed_only(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Patch completed only")
        resp = await client.patch(f"/todos/{todo['id']}", json={"completed": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Patch completed only"  # unchanged
        assert data["completed"] is True

    async def test_patch_both_fields(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Patch both")
        resp = await client.patch(
            f"/todos/{todo['id']}",
            json={"title": "Both updated", "completed": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Both updated"
        assert data["completed"] is True

    async def test_patch_empty_body_returns_422(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Empty patch")
        resp = await client.patch(f"/todos/{todo['id']}", json={})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "At least one field must be provided"

    async def test_patch_only_unknown_fields_returns_422(
        self, client: AsyncClient
    ) -> None:
        todo = await _create_todo(client, "Unknown patch")
        resp = await client.patch(f"/todos/{todo['id']}", json={"foo": "bar"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "At least one field must be provided"

    async def test_patch_duplicate_title_returns_409(self, client: AsyncClient) -> None:
        await _create_todo(client, "Dup target")
        todo2 = await _create_todo(client, "Dup source")
        resp = await client.patch(f"/todos/{todo2['id']}", json={"title": "dup target"})
        assert resp.status_code == 409
        assert resp.json()["detail"] == "A todo with this title already exists"

    async def test_patch_same_title_as_self_succeeds(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Buy Milk Patch")
        resp = await client.patch(
            f"/todos/{todo['id']}", json={"title": "buy milk patch"}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "buy milk patch"

    async def test_patch_nonexistent_id_returns_404(self, client: AsyncClient) -> None:
        resp = await client.patch("/todos/99999", json={"title": "No exist"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    async def test_patch_non_integer_id_returns_422(self, client: AsyncClient) -> None:
        resp = await client.patch("/todos/abc", json={"title": "Bad id"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"

    async def test_patch_trims_title(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Trim patch")
        resp = await client.patch(f"/todos/{todo['id']}", json={"title": "  New  "})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    async def test_patch_completed_string_returns_422(
        self, client: AsyncClient
    ) -> None:
        todo = await _create_todo(client, "Str completed")
        resp = await client.patch(f"/todos/{todo['id']}", json={"completed": "yes"})
        assert resp.status_code == 422

    async def test_patch_completed_integer_returns_422(
        self, client: AsyncClient
    ) -> None:
        todo = await _create_todo(client, "Int completed")
        resp = await client.patch(f"/todos/{todo['id']}", json={"completed": 123})
        assert resp.status_code == 422


# ===========================================================================
# POST /todos/{id}/complete
# ===========================================================================


class TestMarkComplete:
    """POST /todos/{id}/complete."""

    async def test_mark_complete(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Complete me")
        resp = await client.post(f"/todos/{todo['id']}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is True
        assert data["title"] == "Complete me"
        assert data["id"] == todo["id"]

    async def test_mark_complete_already_complete_is_idempotent(
        self, client: AsyncClient
    ) -> None:
        todo = await _create_todo(client, "Already complete")
        # Complete it
        await client.post(f"/todos/{todo['id']}/complete")
        # Complete again
        resp = await client.post(f"/todos/{todo['id']}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    async def test_mark_complete_nonexistent_returns_404(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post("/todos/99999/complete")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    async def test_mark_complete_non_integer_id_returns_422(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post("/todos/abc/complete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"


# ===========================================================================
# POST /todos/{id}/incomplete
# ===========================================================================


class TestMarkIncomplete:
    """POST /todos/{id}/incomplete."""

    async def test_mark_incomplete(self, client: AsyncClient) -> None:
        todo = await _create_todo(client, "Incomplete me")
        # First complete it
        await client.post(f"/todos/{todo['id']}/complete")
        # Then mark incomplete
        resp = await client.post(f"/todos/{todo['id']}/incomplete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is False
        assert data["title"] == "Incomplete me"
        assert data["id"] == todo["id"]

    async def test_mark_incomplete_already_incomplete_is_idempotent(
        self, client: AsyncClient
    ) -> None:
        todo = await _create_todo(client, "Already incomplete")
        # Already incomplete by default, mark it again
        resp = await client.post(f"/todos/{todo['id']}/incomplete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is False

    async def test_mark_incomplete_nonexistent_returns_404(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post("/todos/99999/incomplete")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Todo not found"

    async def test_mark_incomplete_non_integer_id_returns_422(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post("/todos/abc/incomplete")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "id must be a positive integer"
