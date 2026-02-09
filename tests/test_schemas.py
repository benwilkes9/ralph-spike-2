"""Tests for Pydantic request/response schemas."""

import pytest
from pydantic import ValidationError

from ralf_spike_2.schemas import (
    PaginatedResponse,
    TodoCreate,
    TodoResponse,
    TodoUpdatePatch,
    TodoUpdatePut,
)

# --- TodoCreate ---


class TestTodoCreate:
    """Tests for the TodoCreate schema."""

    def test_rejects_missing_title(self) -> None:
        """TodoCreate rejects missing title (validation error)."""
        with pytest.raises(ValidationError):
            TodoCreate.model_validate({})

    def test_accepts_valid_title(self) -> None:
        """TodoCreate accepts a valid title."""
        todo = TodoCreate.model_validate({"title": "Buy milk"})
        assert todo.title == "Buy milk"

    def test_ignores_completed_field(self) -> None:
        """TodoCreate silently ignores completed field."""
        todo = TodoCreate.model_validate({"title": "Buy milk", "completed": True})
        assert todo.title == "Buy milk"
        assert not hasattr(todo, "completed")

    def test_ignores_unknown_fields(self) -> None:
        """TodoCreate silently ignores unknown fields."""
        todo = TodoCreate.model_validate({"title": "Buy milk", "foo": "bar", "baz": 42})
        assert todo.title == "Buy milk"
        assert not hasattr(todo, "foo")
        assert not hasattr(todo, "baz")


# --- TodoUpdatePut ---


class TestTodoUpdatePut:
    """Tests for the TodoUpdatePut schema."""

    def test_defaults_completed_to_false(self) -> None:
        """TodoUpdatePut defaults completed to false when omitted."""
        todo = TodoUpdatePut.model_validate({"title": "Updated"})
        assert todo.title == "Updated"
        assert todo.completed is False

    def test_accepts_completed_true(self) -> None:
        """TodoUpdatePut accepts completed=true."""
        todo = TodoUpdatePut.model_validate({"title": "Updated", "completed": True})
        assert todo.completed is True

    def test_rejects_missing_title(self) -> None:
        """TodoUpdatePut rejects missing title."""
        with pytest.raises(ValidationError):
            TodoUpdatePut.model_validate({"completed": True})

    def test_rejects_non_bool_completed(self) -> None:
        """TodoUpdatePut rejects non-boolean completed (strict mode)."""
        with pytest.raises(ValidationError):
            TodoUpdatePut.model_validate({"title": "Test", "completed": "yes"})

    def test_rejects_int_completed(self) -> None:
        """TodoUpdatePut rejects integer completed (strict mode)."""
        with pytest.raises(ValidationError):
            TodoUpdatePut.model_validate({"title": "Test", "completed": 1})

    def test_ignores_unknown_fields(self) -> None:
        """TodoUpdatePut silently ignores unknown fields."""
        todo = TodoUpdatePut.model_validate({"title": "Updated", "foo": "bar"})
        assert todo.title == "Updated"
        assert not hasattr(todo, "foo")


# --- TodoUpdatePatch ---


class TestTodoUpdatePatch:
    """Tests for the TodoUpdatePatch schema."""

    def test_accepts_title_only(self) -> None:
        """TodoUpdatePatch accepts title only."""
        todo = TodoUpdatePatch.model_validate({"title": "New"})
        assert todo.title == "New"
        assert todo.completed is None

    def test_accepts_completed_only(self) -> None:
        """TodoUpdatePatch accepts completed only."""
        todo = TodoUpdatePatch.model_validate({"completed": True})
        assert todo.completed is True
        assert todo.title is None

    def test_accepts_both_fields(self) -> None:
        """TodoUpdatePatch accepts both title and completed."""
        todo = TodoUpdatePatch.model_validate({"title": "New", "completed": True})
        assert todo.title == "New"
        assert todo.completed is True

    def test_rejects_empty_body(self) -> None:
        """TodoUpdatePatch raises error when no fields provided."""
        with pytest.raises(
            ValidationError, match="At least one field must be provided"
        ):
            TodoUpdatePatch.model_validate({})

    def test_rejects_only_unknown_fields(self) -> None:
        """TodoUpdatePatch treats only unknown fields as empty."""
        with pytest.raises(
            ValidationError, match="At least one field must be provided"
        ):
            TodoUpdatePatch.model_validate({"foo": "bar", "baz": 42})

    def test_ignores_unknown_fields_with_valid(self) -> None:
        """TodoUpdatePatch ignores unknown fields when valid fields present."""
        todo = TodoUpdatePatch.model_validate({"title": "New", "foo": "bar"})
        assert todo.title == "New"
        assert not hasattr(todo, "foo")

    def test_rejects_non_bool_completed(self) -> None:
        """TodoUpdatePatch rejects non-boolean completed (strict mode)."""
        with pytest.raises(ValidationError):
            TodoUpdatePatch.model_validate({"completed": "yes"})

    def test_rejects_int_completed(self) -> None:
        """TodoUpdatePatch rejects integer completed (strict mode)."""
        with pytest.raises(ValidationError):
            TodoUpdatePatch.model_validate({"completed": 123})


# --- TodoResponse ---


class TestTodoResponse:
    """Tests for the TodoResponse schema."""

    def test_serialises_all_fields(self) -> None:
        """TodoResponse serialises all three fields correctly."""
        todo = TodoResponse(id=1, title="Buy milk", completed=False)
        data = todo.model_dump()
        assert data == {"id": 1, "title": "Buy milk", "completed": False}

    def test_serialises_completed_true(self) -> None:
        """TodoResponse serialises completed=true correctly."""
        todo = TodoResponse(id=2, title="Done", completed=True)
        data = todo.model_dump()
        assert data["completed"] is True

    def test_json_serialisation(self) -> None:
        """TodoResponse can serialise to JSON-compatible dict."""
        todo = TodoResponse(id=1, title="Test", completed=False)
        json_data = todo.model_dump(mode="json")
        assert json_data == {"id": 1, "title": "Test", "completed": False}


# --- PaginatedResponse ---


class TestPaginatedResponse:
    """Tests for the PaginatedResponse schema."""

    def test_serialises_envelope(self) -> None:
        """PaginatedResponse serialises envelope correctly."""
        items = [
            TodoResponse(id=1, title="First", completed=False),
            TodoResponse(id=2, title="Second", completed=True),
        ]
        paginated = PaginatedResponse(items=items, page=1, per_page=10, total=2)
        data = paginated.model_dump()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0] == {
            "id": 1,
            "title": "First",
            "completed": False,
        }
        assert data["items"][1] == {
            "id": 2,
            "title": "Second",
            "completed": True,
        }

    def test_empty_items(self) -> None:
        """PaginatedResponse works with empty items list."""
        paginated = PaginatedResponse(items=[], page=1, per_page=10, total=0)
        data = paginated.model_dump()
        assert data["items"] == []
        assert data["total"] == 0
