"""Pydantic schemas for request/response validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TodoResponse(BaseModel):
    """Schema for todo responses."""

    id: int
    title: str
    completed: bool


class TodoCreate(BaseModel):
    """Schema for creating a todo. Extra fields are ignored."""

    model_config = {"extra": "ignore"}

    title: Any = None
    completed: Any = None


class TodoUpdate(BaseModel):
    """Schema for PUT update (full replacement). Extra fields are ignored."""

    model_config = {"extra": "ignore"}

    title: Any = None
    completed: Any = None


class PaginatedResponse(BaseModel):
    """Envelope for paginated list responses."""

    items: list[TodoResponse]
    page: int
    per_page: int
    total: int
