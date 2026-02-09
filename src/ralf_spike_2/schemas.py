"""Pydantic models for request/response shapes."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TodoCreate(BaseModel):
    """Schema for creating a new todo. Only title is accepted."""

    model_config = ConfigDict(extra="ignore")

    title: str


class TodoUpdatePut(BaseModel):
    """Schema for full replacement of a todo (PUT)."""

    model_config = ConfigDict(extra="ignore")

    title: str
    completed: bool = Field(default=False, strict=True)


class TodoUpdatePatch(BaseModel):
    """Schema for partial update of a todo (PATCH)."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    completed: bool | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "TodoUpdatePatch":
        """Ensure at least one recognized field is provided."""
        if self.title is None and self.completed is None:
            raise ValueError("At least one field must be provided")
        return self


class TodoResponse(BaseModel):
    """Schema for a single todo in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    completed: bool


class PaginatedResponse(BaseModel):
    """Pagination envelope for list responses."""

    items: list[TodoResponse]
    page: int
    per_page: int
    total: int
