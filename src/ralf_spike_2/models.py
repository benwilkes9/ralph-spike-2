"""Pydantic schemas for request/response models."""

from __future__ import annotations

from pydantic import BaseModel, StrictBool, StrictStr


class TodoCreate(BaseModel):
    """Request body for creating a todo."""

    model_config = {"extra": "ignore"}

    title: StrictStr


class TodoUpdate(BaseModel):
    """Request body for full todo replacement (PUT)."""

    model_config = {"extra": "ignore"}

    title: StrictStr
    completed: StrictBool = False


class TodoPatch(BaseModel):
    """Request body for partial todo update (PATCH)."""

    model_config = {"extra": "ignore"}

    title: StrictStr | None = None
    completed: StrictBool | None = None


class TodoResponse(BaseModel):
    """Response body for a single todo."""

    id: int
    title: str
    completed: bool


class PaginatedResponse(BaseModel):
    """Paginated list response."""

    items: list[TodoResponse]
    page: int
    per_page: int
    total: int
