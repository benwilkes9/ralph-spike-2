"""Todo API route handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from ralf_spike_2.database import get_session
from ralf_spike_2.models import Todo
from ralf_spike_2.schemas import (
    PaginatedResponse,
    TodoCreate,
    TodoResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


_SQLITE_MAX_INT = 2**63 - 1


def _validate_path_id(todo_id: str) -> int | None:
    """Validate path parameter is a positive integer.

    Returns the integer id or None if invalid.
    """
    try:
        val = int(todo_id)
    except (ValueError, TypeError):
        return None
    if val <= 0:
        return None
    # Reject floats like "1.5" that got truncated
    if "." in todo_id:
        return None
    # Reject values too large for SQLite INTEGER
    if val > _SQLITE_MAX_INT:
        return None
    return val


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


async def _parse_json_body(request: Request) -> dict[str, Any] | JSONResponse:
    """Parse request body as a JSON object.

    Returns the dict or a 422 JSONResponse if body is not a JSON object.
    """
    body: Any = await request.json()
    if not isinstance(body, dict):
        return _error_response(422, "Request body must be a JSON object")
    return cast("dict[str, Any]", body)


def _validate_title_value(title: Any) -> JSONResponse | None:
    """Validate title type and format. Returns error response or None."""
    if not isinstance(title, str):
        return _error_response(422, "title must be a string")
    trimmed = title.strip()
    if not trimmed:
        return _error_response(422, "title must not be blank")
    if len(trimmed) > 500:
        return _error_response(422, "title must be 500 characters or fewer")
    return None


async def _check_title_unique(
    session: AsyncSession, title: str, exclude_id: int | None = None
) -> JSONResponse | None:
    """Check case-insensitive title uniqueness. Returns 409 or None."""
    trimmed = title.strip()
    query = select(Todo).where(func.lower(Todo.title) == trimmed.lower())
    if exclude_id is not None:
        query = query.where(Todo.id != exclude_id)
    result = await session.execute(query)
    existing = result.scalar_one_or_none()
    if existing is not None:
        return _error_response(409, "A todo with this title already exists")
    return None


@router.post("/todos", response_model=None)
async def create_todo(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Create a new todo."""
    parsed = await _parse_json_body(request)
    if isinstance(parsed, JSONResponse):
        return parsed
    body: dict[str, Any] = parsed

    # Parse through schema to strip unknown fields
    data = TodoCreate.model_validate(body)

    # Validation order: missing -> type -> blank -> length -> uniqueness
    if data.title is None:
        return _error_response(422, "title is required")

    title_err = _validate_title_value(data.title)
    if title_err is not None:
        return title_err

    trimmed_title: str = data.title.strip()

    uniqueness_err = await _check_title_unique(session, trimmed_title)
    if uniqueness_err is not None:
        return uniqueness_err

    todo = Todo(title=trimmed_title, completed=False)
    session.add(todo)
    await session.commit()
    await session.refresh(todo)

    response_data = TodoResponse(id=todo.id, title=todo.title, completed=todo.completed)
    return JSONResponse(
        status_code=201,
        content=response_data.model_dump(),
    )


@router.get("/todos", response_model=None)
async def list_todos(
    request: Request,
    session: AsyncSession = Depends(get_session),
    completed: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
    page: str | None = Query(default=None),
    per_page: str | None = Query(default=None),
) -> Any:
    """List todos with optional filtering, sorting, and pagination."""
    has_params = bool(request.query_params)

    query = select(Todo)

    # Validate and apply completed filter
    if completed is not None:
        if completed not in ("true", "false"):
            return _error_response(422, "completed must be true or false")
        query = query.where(Todo.completed == (completed == "true"))

    # Apply search filter (escape LIKE wildcards for literal substring match)
    if search is not None and search != "":
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Todo.title.ilike(f"%{escaped}%", escape="\\"))

    # Validate sort
    sort_field = sort if sort is not None else "id"
    if sort_field not in ("id", "title"):
        return _error_response(422, "sort must be 'id' or 'title'")

    # Validate order
    order_dir = order if order is not None else "desc"
    if order_dir not in ("asc", "desc"):
        return _error_response(422, "order must be 'asc' or 'desc'")

    # Apply sorting
    sort_col = func.lower(Todo.title) if sort_field == "title" else Todo.id
    if order_dir == "asc":
        query = query.order_by(sort_col.asc())  # type: ignore[union-attr]
    else:
        query = query.order_by(sort_col.desc())  # type: ignore[union-attr]

    if not has_params:
        # Plain array response
        result = await session.execute(query)
        todos = result.scalars().all()
        return [
            TodoResponse(id=t.id, title=t.title, completed=t.completed).model_dump()
            for t in todos
        ]

    # Paginated envelope response
    # Validate page
    page_num = 1
    if page is not None:
        try:
            page_num = int(page)
            if page_num < 1:
                return _error_response(422, "page must be a positive integer")
        except (ValueError, TypeError):
            return _error_response(422, "page must be a positive integer")

    # Validate per_page
    per_page_num = 10
    if per_page is not None:
        try:
            per_page_num = int(per_page)
            if per_page_num < 1 or per_page_num > 100:
                per_page_msg = "per_page must be an integer between 1 and 100"
                return _error_response(422, per_page_msg)
        except (ValueError, TypeError):
            per_page_msg = "per_page must be an integer between 1 and 100"
            return _error_response(422, per_page_msg)

    # Count total matching items
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page_num - 1) * per_page_num
    paginated_query = query.offset(offset).limit(per_page_num)
    result = await session.execute(paginated_query)
    todos = result.scalars().all()

    return PaginatedResponse(
        items=[
            TodoResponse(id=t.id, title=t.title, completed=t.completed) for t in todos
        ],
        page=page_num,
        per_page=per_page_num,
        total=total,
    ).model_dump()


@router.get("/todos/{todo_id}", response_model=None)
async def get_todo(
    todo_id: str,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Get a single todo by id."""
    validated_id = _validate_path_id(todo_id)
    if validated_id is None:
        return _error_response(422, "id must be a positive integer")

    result = await session.execute(select(Todo).where(Todo.id == validated_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        return _error_response(404, "Todo not found")

    return TodoResponse(
        id=todo.id, title=todo.title, completed=todo.completed
    ).model_dump()


@router.put("/todos/{todo_id}", response_model=None)
async def update_todo(
    todo_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Full replacement update of a todo."""
    validated_id = _validate_path_id(todo_id)
    if validated_id is None:
        return _error_response(422, "id must be a positive integer")

    result = await session.execute(select(Todo).where(Todo.id == validated_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        return _error_response(404, "Todo not found")

    parsed = await _parse_json_body(request)
    if isinstance(parsed, JSONResponse):
        return parsed
    raw_body: dict[str, Any] = parsed

    # Validation order: missing -> type -> blank -> length -> uniqueness
    # Priority 1: Missing required field
    if "title" not in raw_body:
        return _error_response(422, "title is required")

    # Priority 2: Type errors (all fields checked before blank/length)
    title_val: Any = raw_body.get("title")
    if title_val is None:
        return _error_response(422, "title is required")
    if not isinstance(title_val, str):
        return _error_response(422, "title must be a string")
    has_completed = "completed" in raw_body
    completed_val = False
    if has_completed:
        completed_raw: Any = raw_body["completed"]
        if not isinstance(completed_raw, bool):
            return _error_response(422, "completed must be a boolean")
        completed_val = completed_raw

    # Priority 3-4: Blank and length (title only)
    trimmed_title: str = title_val.strip()
    if not trimmed_title:
        return _error_response(422, "title must not be blank")
    if len(trimmed_title) > 500:
        return _error_response(422, "title must be 500 characters or fewer")

    # Priority 5: Uniqueness
    uniqueness_err = await _check_title_unique(
        session, trimmed_title, exclude_id=validated_id
    )
    if uniqueness_err is not None:
        return uniqueness_err

    todo.title = trimmed_title
    todo.completed = completed_val
    await session.commit()
    await session.refresh(todo)

    return TodoResponse(
        id=todo.id, title=todo.title, completed=todo.completed
    ).model_dump()


@router.patch("/todos/{todo_id}", response_model=None)
async def patch_todo(
    todo_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Partial update of a todo."""
    validated_id = _validate_path_id(todo_id)
    if validated_id is None:
        return _error_response(422, "id must be a positive integer")

    result = await session.execute(select(Todo).where(Todo.id == validated_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        return _error_response(404, "Todo not found")

    parsed = await _parse_json_body(request)
    if isinstance(parsed, JSONResponse):
        return parsed
    body: dict[str, Any] = parsed

    # Check which recognized fields are present in raw body
    has_title = "title" in body
    has_completed = "completed" in body

    if not has_title and not has_completed:
        return _error_response(422, "At least one field must be provided")

    # Priority 2: Type errors (all fields before blank/length)
    title_val: Any = body.get("title")
    completed_val: Any = body.get("completed")
    if has_title and not isinstance(title_val, str):
        return _error_response(422, "title must be a string")
    if has_completed and not isinstance(completed_val, bool):
        return _error_response(422, "completed must be a boolean")

    # Priority 3-4: Blank and length (title only)
    if has_title:
        assert isinstance(title_val, str)
        trimmed_title: str = title_val.strip()
        if not trimmed_title:
            return _error_response(422, "title must not be blank")
        if len(trimmed_title) > 500:
            return _error_response(422, "title must be 500 characters or fewer")

        # Priority 5: Uniqueness
        uniqueness_err = await _check_title_unique(
            session, trimmed_title, exclude_id=validated_id
        )
        if uniqueness_err is not None:
            return uniqueness_err
        todo.title = trimmed_title

    if has_completed:
        assert isinstance(completed_val, bool)
        todo.completed = completed_val

    await session.commit()
    await session.refresh(todo)

    return TodoResponse(
        id=todo.id, title=todo.title, completed=todo.completed
    ).model_dump()


@router.post("/todos/{todo_id}/complete", response_model=None)
async def complete_todo(
    todo_id: str,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Mark a todo as complete."""
    validated_id = _validate_path_id(todo_id)
    if validated_id is None:
        return _error_response(422, "id must be a positive integer")

    result = await session.execute(select(Todo).where(Todo.id == validated_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        return _error_response(404, "Todo not found")

    todo.completed = True
    await session.commit()
    await session.refresh(todo)

    return TodoResponse(
        id=todo.id, title=todo.title, completed=todo.completed
    ).model_dump()


@router.post("/todos/{todo_id}/incomplete", response_model=None)
async def incomplete_todo(
    todo_id: str,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Mark a todo as incomplete."""
    validated_id = _validate_path_id(todo_id)
    if validated_id is None:
        return _error_response(422, "id must be a positive integer")

    result = await session.execute(select(Todo).where(Todo.id == validated_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        return _error_response(404, "Todo not found")

    todo.completed = False
    await session.commit()
    await session.refresh(todo)

    return TodoResponse(
        id=todo.id, title=todo.title, completed=todo.completed
    ).model_dump()


@router.delete("/todos/{todo_id}", response_model=None)
async def delete_todo(
    todo_id: str,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Delete a todo."""
    validated_id = _validate_path_id(todo_id)
    if validated_id is None:
        return _error_response(422, "id must be a positive integer")

    result = await session.execute(select(Todo).where(Todo.id == validated_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        return _error_response(404, "Todo not found")

    await session.delete(todo)
    await session.commit()

    return Response(status_code=204)
