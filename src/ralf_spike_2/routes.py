"""API route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ralf_spike_2.database import get_db
from ralf_spike_2.models import Todo
from ralf_spike_2.schemas import TodoCreate, TodoResponse

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/todos", response_model=TodoResponse, status_code=201)
def create_todo(body: TodoCreate, db: DbSession) -> JSONResponse | Todo:
    """Create a new todo item."""
    title = body.title.strip()

    # Validate: non-blank after trimming
    if not title:
        return JSONResponse(
            status_code=422,
            content={"detail": "title must not be blank"},
        )

    # Validate: max 500 chars (after trimming)
    if len(title) > 500:
        return JSONResponse(
            status_code=422,
            content={"detail": "title must be 500 characters or fewer"},
        )

    # Create the todo (completed always defaults to false)
    todo = Todo(title=title, completed=False)
    db.add(todo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=409,
            content={"detail": "A todo with this title already exists"},
        )
    db.refresh(todo)
    return todo
