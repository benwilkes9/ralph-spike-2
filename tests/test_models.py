"""Tests for Pydantic models (Task 2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ralf_spike_2.models import (
    PaginatedResponse,
    TodoCreate,
    TodoPatch,
    TodoResponse,
    TodoUpdate,
)


def test_todo_create_valid() -> None:
    """TodoCreate accepts valid title."""
    m = TodoCreate(title="Buy milk")
    assert m.title == "Buy milk"


def test_todo_create_rejects_missing_title() -> None:
    """TodoCreate rejects missing title."""
    with pytest.raises(ValidationError):
        TodoCreate()  # type: ignore[call-arg]


def test_todo_create_ignores_unknown_fields() -> None:
    """TodoCreate ignores unknown fields."""
    m = TodoCreate(title="Buy milk", priority="high")  # type: ignore[call-arg]
    assert m.title == "Buy milk"
    assert not hasattr(m, "priority")


def test_todo_update_defaults_completed_false() -> None:
    """TodoUpdate defaults completed to false."""
    m = TodoUpdate(title="Buy milk")
    assert m.completed is False


def test_todo_update_with_completed() -> None:
    """TodoUpdate accepts completed=true."""
    m = TodoUpdate(title="Buy milk", completed=True)
    assert m.completed is True


def test_todo_patch_all_none() -> None:
    """TodoPatch allows both fields to be None."""
    m = TodoPatch()
    assert m.title is None
    assert m.completed is None


def test_todo_patch_partial() -> None:
    """TodoPatch accepts partial fields."""
    m = TodoPatch(completed=True)
    assert m.title is None
    assert m.completed is True


def test_todo_response() -> None:
    """TodoResponse serializes correctly."""
    m = TodoResponse(id=1, title="Buy milk", completed=False)
    assert m.id == 1
    assert m.title == "Buy milk"
    assert m.completed is False


def test_paginated_response() -> None:
    """PaginatedResponse includes all fields."""
    items = [TodoResponse(id=1, title="Buy milk", completed=False)]
    m = PaginatedResponse(items=items, page=1, per_page=10, total=1)
    assert len(m.items) == 1
    assert m.total == 1
