"""Pydantic schemas for request/response models."""

from pydantic import BaseModel, StrictBool


class TodoCreate(BaseModel):
    """Schema for creating a todo."""

    title: str


class TodoUpdate(BaseModel):
    """Schema for full replacement of a todo (PUT)."""

    title: str
    completed: bool = False

    model_config = {"extra": "ignore"}


class TodoPatch(BaseModel):
    """Schema for partial update of a todo (PATCH)."""

    title: str | None = None
    completed: StrictBool | None = None

    model_config = {"extra": "ignore"}


class TodoResponse(BaseModel):
    """Schema for todo response."""

    id: int
    title: str
    completed: bool

    model_config = {"from_attributes": True}


class PaginatedTodoResponse(BaseModel):
    """Schema for paginated todo list response."""

    items: list[TodoResponse]
    page: int
    per_page: int
    total: int
