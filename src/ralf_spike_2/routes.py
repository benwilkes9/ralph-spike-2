"""Todo API route handlers."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ralf_spike_2.errors import DuplicateTitleError, validate_title
from ralf_spike_2.models import TodoModel
from ralf_spike_2.schemas import TodoCreate, TodoResponse

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
