"""Pydantic schemas for request/response models."""

from pydantic import BaseModel


class TodoCreate(BaseModel):
    """Schema for creating a todo."""

    title: str


class TodoResponse(BaseModel):
    """Schema for todo response."""

    id: int
    title: str
    completed: bool

    model_config = {"from_attributes": True}
