"""Pydantic schemas for request/response models."""

from pydantic import BaseModel


class TodoCreate(BaseModel):
    """Schema for creating a todo."""

    title: str


class TodoUpdate(BaseModel):
    """Schema for full replacement of a todo (PUT)."""

    title: str
    completed: bool = False

    model_config = {"extra": "ignore"}


class TodoResponse(BaseModel):
    """Schema for todo response."""

    id: int
    title: str
    completed: bool

    model_config = {"from_attributes": True}
