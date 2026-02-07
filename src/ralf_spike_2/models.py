"""Pydantic models for Todo API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TodoResponse(BaseModel):
    """Response schema for a single todo."""

    id: int
    title: str
    completed: bool


class TodoCreate(BaseModel):
    """Request schema for creating a todo (POST)."""

    title: str | None = None
    completed: object | None = None  # accept any type so we can validate manually

    model_config = {"extra": "ignore"}


class TodoUpdate(BaseModel):
    """Request schema for full update (PUT)."""

    title: str | None = None
    completed: object | None = None

    model_config = {"extra": "ignore"}


class TodoPatch(BaseModel):
    """Request schema for partial update (PATCH).

    We use a sentinel to distinguish between 'field not provided' and 'field is None'.
    """

    model_config = {"extra": "ignore"}


class PaginatedResponse(BaseModel):
    """Paginated list response envelope."""

    items: list[TodoResponse]
    page: int
    per_page: int
    total: int
