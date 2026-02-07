"""Todo API route handlers."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request, Response

from ralf_spike_2 import database as db
from ralf_spike_2.models import PaginatedResponse, TodoResponse

router = APIRouter()


class HTTPError(Exception):
    """Custom HTTP error with status code and detail message."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _validate_path_id(id_str: str) -> int:
    """Validate that path id is a positive integer."""
    try:
        todo_id = int(id_str)
    except (ValueError, TypeError):
        raise HTTPError(
            status_code=422, detail="id must be a positive integer"
        ) from None
    if todo_id <= 0:
        raise HTTPError(status_code=422, detail="id must be a positive integer")
    return todo_id


def _validate_title(
    title: Any,
    required: bool = True,
    exclude_id: int | None = None,
) -> str:
    """Validate title field following the priority order:
    missing -> type -> blank -> length -> uniqueness.
    Returns trimmed title.
    """
    # Missing check
    if title is None:
        if required:
            raise HTTPError(status_code=422, detail="title is required")
        return ""

    # Type check
    if not isinstance(title, str):
        raise HTTPError(status_code=422, detail="title must be a string")

    # Trim
    trimmed = title.strip()

    # Blank check
    if not trimmed:
        raise HTTPError(status_code=422, detail="title must not be blank")

    # Length check
    if len(trimmed) > 500:
        raise HTTPError(
            status_code=422,
            detail="title must be 500 characters or fewer",
        )

    # Uniqueness check
    if not db.check_title_unique(trimmed, exclude_id=exclude_id):
        raise HTTPError(
            status_code=409,
            detail="A todo with this title already exists",
        )

    return trimmed


def _validate_completed(value: Any) -> bool:
    """Validate completed field is a boolean."""
    if not isinstance(value, bool):
        raise HTTPError(status_code=422, detail="completed must be a boolean")
    return value


async def _parse_body(request: Request) -> dict[str, Any]:
    """Parse JSON body, returning dict.

    Unknown fields are kept but ignored downstream.
    """
    body = await request.body()
    if not body:
        return {}
    try:
        data: Any = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPError(status_code=422, detail="Invalid JSON body") from None
    if not isinstance(data, dict):
        raise HTTPError(
            status_code=422,
            detail="Request body must be a JSON object",
        )
    return data  # type: ignore[no-any-return]


# --- POST /todos ---


@router.post("/todos", status_code=201)
async def create_todo(request: Request) -> TodoResponse:
    """Create a new todo."""
    data = await _parse_body(request)

    title = data.get("title")
    trimmed = _validate_title(title, required=True)

    # completed is not accepted on creation - always false
    todo = db.create_todo(trimmed)
    return TodoResponse(**todo)


# --- GET /todos ---


@router.get("/todos")
async def list_todos(request: Request) -> Any:
    """List all todos or query with filters."""
    params = dict(request.query_params)

    # If no query params, return plain array
    if not params:
        todos = db.get_all_todos()
        return [TodoResponse(**t) for t in todos]

    # Parse and validate query params
    completed: bool | None = None
    if "completed" in params:
        val = params["completed"]
        if val == "true":
            completed = True
        elif val == "false":
            completed = False
        else:
            raise HTTPError(
                status_code=422,
                detail="completed must be true or false",
            )

    search: str | None = params.get("search")
    if search == "":
        search = None

    sort = params.get("sort", "id")
    if sort not in ("id", "title"):
        raise HTTPError(
            status_code=422,
            detail="sort must be 'id' or 'title'",
        )

    order = params.get("order", "desc")
    if order not in ("asc", "desc"):
        raise HTTPError(
            status_code=422,
            detail="order must be 'asc' or 'desc'",
        )

    # Page validation
    page_str = params.get("page", "1")
    try:
        page = int(page_str)
    except ValueError:
        raise HTTPError(
            status_code=422,
            detail="page must be a positive integer",
        ) from None
    if page < 1:
        raise HTTPError(
            status_code=422,
            detail="page must be a positive integer",
        )

    # Per page validation
    per_page_str = params.get("per_page", "10")
    try:
        per_page = int(per_page_str)
    except ValueError:
        raise HTTPError(
            status_code=422,
            detail="per_page must be an integer between 1 and 100",
        ) from None
    if per_page < 1 or per_page > 100:
        raise HTTPError(
            status_code=422,
            detail="per_page must be an integer between 1 and 100",
        )

    items, total = db.query_todos(
        completed=completed,
        search=search,
        sort=sort,
        order=order,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        items=[TodoResponse(**t) for t in items],
        page=page,
        per_page=per_page,
        total=total,
    )


# --- GET /todos/{id} ---


@router.get("/todos/{todo_id}")
async def get_todo(todo_id: str) -> TodoResponse:
    """Get a single todo by ID."""
    tid = _validate_path_id(todo_id)
    todo = db.get_todo_by_id(tid)
    if todo is None:
        raise HTTPError(status_code=404, detail="Todo not found")
    return TodoResponse(**todo)


# --- PUT /todos/{id} ---


@router.put("/todos/{todo_id}")
async def update_todo(
    todo_id: str,
    request: Request,
) -> TodoResponse:
    """Full update of a todo."""
    tid = _validate_path_id(todo_id)

    # Check existence first
    existing = db.get_todo_by_id(tid)
    if existing is None:
        raise HTTPError(status_code=404, detail="Todo not found")

    data = await _parse_body(request)

    # Title is required for PUT
    title = data.get("title")
    trimmed = _validate_title(title, required=True, exclude_id=tid)

    # Completed defaults to false if omitted
    completed_val = data.get("completed")
    completed = False if completed_val is None else _validate_completed(completed_val)

    todo = db.update_todo(tid, trimmed, completed)
    if todo is None:
        raise HTTPError(status_code=404, detail="Todo not found")
    return TodoResponse(**todo)


# --- PATCH /todos/{id} ---


@router.patch("/todos/{todo_id}")
async def patch_todo(
    todo_id: str,
    request: Request,
) -> TodoResponse:
    """Partial update of a todo."""
    tid = _validate_path_id(todo_id)

    # Check existence first
    existing = db.get_todo_by_id(tid)
    if existing is None:
        raise HTTPError(status_code=404, detail="Todo not found")

    data = await _parse_body(request)

    # Check at least one recognised field
    recognised = {"title", "completed"}
    provided = recognised & set(data.keys())
    if not provided:
        raise HTTPError(
            status_code=422,
            detail="At least one field must be provided",
        )

    title: str | None = None
    completed: bool | None = None

    if "title" in data:
        title = _validate_title(
            data["title"],
            required=True,
            exclude_id=tid,
        )

    if "completed" in data:
        completed = _validate_completed(data["completed"])

    todo = db.patch_todo(tid, title=title, completed=completed)
    if todo is None:
        raise HTTPError(status_code=404, detail="Todo not found")
    return TodoResponse(**todo)


# --- POST /todos/{id}/complete ---


@router.post("/todos/{todo_id}/complete")
async def complete_todo(todo_id: str) -> TodoResponse:
    """Mark a todo as complete."""
    tid = _validate_path_id(todo_id)
    existing = db.get_todo_by_id(tid)
    if existing is None:
        raise HTTPError(status_code=404, detail="Todo not found")
    todo = db.patch_todo(tid, completed=True)
    if todo is None:
        raise HTTPError(status_code=404, detail="Todo not found")
    return TodoResponse(**todo)


# --- POST /todos/{id}/incomplete ---


@router.post("/todos/{todo_id}/incomplete")
async def incomplete_todo(todo_id: str) -> TodoResponse:
    """Mark a todo as incomplete."""
    tid = _validate_path_id(todo_id)
    existing = db.get_todo_by_id(tid)
    if existing is None:
        raise HTTPError(status_code=404, detail="Todo not found")
    todo = db.patch_todo(tid, completed=False)
    if todo is None:
        raise HTTPError(status_code=404, detail="Todo not found")
    return TodoResponse(**todo)


# --- DELETE /todos/{id} ---


@router.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: str) -> Response:
    """Delete a todo."""
    tid = _validate_path_id(todo_id)
    deleted = db.delete_todo(tid)
    if not deleted:
        raise HTTPError(status_code=404, detail="Todo not found")
    return Response(status_code=204)
