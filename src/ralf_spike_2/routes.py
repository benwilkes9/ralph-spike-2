"""Todo API route handlers."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ralf_spike_2.errors import (
    DuplicateTitleError,
    TodoNotFoundError,
    validate_path_id,
    validate_title,
)
from ralf_spike_2.models import TodoModel
from ralf_spike_2.schemas import (
    PaginatedResponse,
    TodoCreate,
    TodoResponse,
    TodoUpdatePatch,
    TodoUpdatePut,
)

router = APIRouter()


async def get_db_stub() -> AsyncIterator[AsyncSession]:
    """Placeholder dependency; overridden by app.py at startup."""
    raise NotImplementedError  # pragma: no cover
    yield  # pragma: no cover


DbSession = Annotated[AsyncSession, Depends(get_db_stub)]


async def _check_title_unique(
    session: AsyncSession, title_lower: str, *, exclude_id: int | None = None
) -> None:
    """Raise DuplicateTitleError if a todo with the same lower-case title exists."""
    stmt = select(TodoModel).where(TodoModel.title_lower == title_lower)
    if exclude_id is not None:
        stmt = stmt.where(TodoModel.id != exclude_id)
    result = await session.execute(stmt)
    if result.scalars().first() is not None:
        raise DuplicateTitleError()


@router.post("/todos", status_code=201, response_model=TodoResponse)
async def create_todo(
    body: TodoCreate,
    db: DbSession,
) -> TodoResponse:
    """Create a new todo item."""
    trimmed_title = validate_title(body.title)
    title_lower = trimmed_title.lower()

    await _check_title_unique(db, title_lower)

    todo = TodoModel(
        title=trimmed_title,
        title_lower=title_lower,
        completed=False,
    )
    db.add(todo)
    await db.commit()
    await db.refresh(todo)

    return TodoResponse.model_validate(todo)


def _validate_completed_param(value: str) -> bool:
    """Validate and parse the completed query parameter."""
    if value == "true":
        return True
    if value == "false":
        return False
    raise HTTPException(status_code=422, detail="completed must be true or false")


def _validate_sort_param(value: str) -> str:
    """Validate the sort query parameter."""
    if value in ("id", "title"):
        return value
    raise HTTPException(status_code=422, detail="sort must be 'id' or 'title'")


def _validate_order_param(value: str) -> str:
    """Validate the order query parameter."""
    if value in ("asc", "desc"):
        return value
    raise HTTPException(status_code=422, detail="order must be 'asc' or 'desc'")


def _validate_page_param(value: str) -> int:
    """Validate and parse the page query parameter."""
    try:
        page = int(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422, detail="page must be a positive integer"
        ) from None
    if page < 1:
        raise HTTPException(status_code=422, detail="page must be a positive integer")
    return page


def _validate_per_page_param(value: str) -> int:
    """Validate and parse the per_page query parameter."""
    try:
        per_page = int(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422,
            detail="per_page must be an integer between 1 and 100",
        ) from None
    if per_page < 1 or per_page > 100:
        raise HTTPException(
            status_code=422,
            detail="per_page must be an integer between 1 and 100",
        )
    return per_page


@router.get("/todos")
async def list_todos(
    request: Request,
    db: DbSession,
) -> list[TodoResponse] | PaginatedResponse:
    """Return todos, optionally with filtering, sorting, and pagination.

    When no query parameters are present, returns a plain JSON array
    (backward compatible). When any query parameter is present, returns
    a pagination envelope.
    """
    has_params = len(request.query_params) > 0

    # --- Validate query parameters ---
    completed_filter: bool | None = None
    search_term: str | None = None
    sort_field = "id"
    order_dir = "desc"
    page = 1
    per_page = 10

    if "completed" in request.query_params:
        completed_filter = _validate_completed_param(request.query_params["completed"])
    if "search" in request.query_params:
        search_term = request.query_params["search"]
    if "sort" in request.query_params:
        sort_field = _validate_sort_param(request.query_params["sort"])
    if "order" in request.query_params:
        order_dir = _validate_order_param(request.query_params["order"])
    if "page" in request.query_params:
        page = _validate_page_param(request.query_params["page"])
    if "per_page" in request.query_params:
        per_page = _validate_per_page_param(request.query_params["per_page"])

    # --- Build query ---
    stmt = select(TodoModel)

    # Filtering
    if completed_filter is not None:
        stmt = stmt.where(TodoModel.completed == completed_filter)

    # Search (case-insensitive substring match on title)
    if search_term is not None and search_term != "":
        stmt = stmt.where(TodoModel.title_lower.like(f"%{search_term.lower()}%"))

    # Sorting
    sort_col = TodoModel.title_lower if sort_field == "title" else TodoModel.id

    if order_dir == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    if not has_params:
        # Plain array mode (backward compatible)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [TodoResponse.model_validate(row) for row in rows]

    # --- Paginated envelope mode ---
    # Count total matching rows
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * per_page
    paginated_stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(paginated_stmt)
    rows = result.scalars().all()
    items = [TodoResponse.model_validate(row) for row in rows]

    return PaginatedResponse(
        items=items,
        page=page,
        per_page=per_page,
        total=total,
    )


@router.get("/todos/{id}", response_model=TodoResponse)
async def get_todo(id: str, db: DbSession) -> TodoResponse:
    """Return a single todo by id."""
    todo_id = validate_path_id(id)
    todo = await _get_todo_or_404(db, todo_id)
    return TodoResponse.model_validate(todo)


async def _get_todo_or_404(session: AsyncSession, todo_id: int) -> TodoModel:
    """Fetch a todo by id or raise 404."""
    stmt = select(TodoModel).where(TodoModel.id == todo_id)
    result = await session.execute(stmt)
    todo = result.scalars().first()
    if todo is None:
        raise TodoNotFoundError()
    return todo


@router.put("/todos/{id}", response_model=TodoResponse)
async def update_todo_put(id: str, body: TodoUpdatePut, db: DbSession) -> TodoResponse:
    """Full replacement of a todo."""
    todo_id = validate_path_id(id)
    todo = await _get_todo_or_404(db, todo_id)

    trimmed_title = validate_title(body.title)
    title_lower = trimmed_title.lower()
    await _check_title_unique(db, title_lower, exclude_id=todo_id)

    todo.title = trimmed_title
    todo.title_lower = title_lower
    todo.completed = body.completed

    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.patch("/todos/{id}", response_model=TodoResponse)
async def update_todo_patch(
    id: str, body: TodoUpdatePatch, db: DbSession
) -> TodoResponse:
    """Partial update of a todo."""
    todo_id = validate_path_id(id)
    todo = await _get_todo_or_404(db, todo_id)

    if body.title is not None:
        trimmed_title = validate_title(body.title)
        title_lower = trimmed_title.lower()
        await _check_title_unique(db, title_lower, exclude_id=todo_id)
        todo.title = trimmed_title
        todo.title_lower = title_lower

    if body.completed is not None:
        todo.completed = body.completed

    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.post("/todos/{id}/complete", response_model=TodoResponse)
async def mark_todo_complete(id: str, db: DbSession) -> TodoResponse:
    """Mark a todo as complete. Idempotent."""
    todo_id = validate_path_id(id)
    todo = await _get_todo_or_404(db, todo_id)

    todo.completed = True
    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.post("/todos/{id}/incomplete", response_model=TodoResponse)
async def mark_todo_incomplete(id: str, db: DbSession) -> TodoResponse:
    """Mark a todo as incomplete. Idempotent."""
    todo_id = validate_path_id(id)
    todo = await _get_todo_or_404(db, todo_id)

    todo.completed = False
    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.delete("/todos/{id}", status_code=204)
async def delete_todo(id: str, db: DbSession) -> Response:
    """Permanently delete a todo by id."""
    todo_id = validate_path_id(id)
    todo = await _get_todo_or_404(db, todo_id)

    await db.delete(todo)
    await db.commit()
    return Response(status_code=204)
