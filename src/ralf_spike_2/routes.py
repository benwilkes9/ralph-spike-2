"""Todo API route handlers."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ralf_spike_2.errors import (
    DuplicateTitleError,
    TodoNotFoundError,
    validate_path_id,
    validate_title,
)
from ralf_spike_2.models import TodoModel
from ralf_spike_2.schemas import (
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


@router.get("/todos", response_model=list[TodoResponse])
async def list_todos(db: DbSession) -> list[TodoResponse]:
    """Return all todos ordered by descending id (newest first)."""
    stmt = select(TodoModel).order_by(TodoModel.id.desc())
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [TodoResponse.model_validate(row) for row in rows]


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
