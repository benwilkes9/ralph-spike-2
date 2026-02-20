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


def _validate_todo_id(todo_id: str) -> int | None:
    """Validate that todo_id is a positive integer."""
    try:
        id_int = int(todo_id)
    except (ValueError, TypeError):
        return None
    if id_int <= 0:
        return None
    return id_int


@router.get("/todos", response_model=list[TodoResponse])
def list_todos(db: DbSession) -> list[Todo]:
    """Return all todos ordered by id descending (newest first)."""
    return list(db.query(Todo).order_by(Todo.id.desc()).all())


@router.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: str, db: DbSession) -> JSONResponse | Todo:
    """Return a single todo by id."""
    id_int = _validate_todo_id(todo_id)
    if id_int is None:
        return JSONResponse(
            status_code=422,
            content={"detail": "id must be a positive integer"},
        )

    todo = db.query(Todo).filter(Todo.id == id_int).first()
    if todo is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "Todo not found"},
        )
    return todo


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
