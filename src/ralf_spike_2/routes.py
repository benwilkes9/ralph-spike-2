"""API route handlers."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ralf_spike_2.database import get_db
from ralf_spike_2.models import Todo
from ralf_spike_2.schemas import TodoCreate, TodoPatch, TodoResponse, TodoUpdate

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


@router.get("/todos")
def list_todos(request: Request, db: DbSession) -> Any:
    """Return todos with optional filtering, sorting, search, and pagination."""
    params = dict(request.query_params)
    has_params = len(params) > 0

    # If no query params, return plain array (backward compatible)
    if not has_params:
        todos = db.query(Todo).order_by(Todo.id.desc()).all()
        return [TodoResponse.model_validate(t) for t in todos]

    # --- Validate query parameters ---

    # completed filter
    completed_filter: bool | None = None
    if "completed" in params:
        val = params["completed"]
        if val == "true":
            completed_filter = True
        elif val == "false":
            completed_filter = False
        else:
            return JSONResponse(
                status_code=422,
                content={"detail": "completed must be true or false"},
            )

    # search
    search: str | None = params.get("search")

    # sort
    sort_field = params.get("sort", "id")
    if sort_field not in ("id", "title"):
        return JSONResponse(
            status_code=422,
            content={"detail": "sort must be 'id' or 'title'"},
        )

    # order
    order = params.get("order", "desc")
    if order not in ("asc", "desc"):
        return JSONResponse(
            status_code=422,
            content={"detail": "order must be 'asc' or 'desc'"},
        )

    # page
    page_str = params.get("page", "1")
    try:
        page = int(page_str)
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=422,
            content={"detail": "page must be a positive integer"},
        )
    if page < 1:
        return JSONResponse(
            status_code=422,
            content={"detail": "page must be a positive integer"},
        )

    # per_page
    per_page_str = params.get("per_page", "10")
    try:
        per_page = int(per_page_str)
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=422,
            content={"detail": "per_page must be an integer between 1 and 100"},
        )
    if per_page < 1 or per_page > 100:
        return JSONResponse(
            status_code=422,
            content={"detail": "per_page must be an integer between 1 and 100"},
        )

    # --- Build query ---
    query = db.query(Todo)

    # Apply filters
    if completed_filter is not None:
        query = query.filter(Todo.completed == completed_filter)

    if search is not None and search != "":
        query = query.filter(Todo.title.ilike(f"%{search}%"))

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    sort_col = func.lower(Todo.title) if sort_field == "title" else Todo.id

    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Apply pagination
    offset = (page - 1) * per_page
    todos = query.offset(offset).limit(per_page).all()

    return {
        "items": [TodoResponse.model_validate(t) for t in todos],
        "page": page,
        "per_page": per_page,
        "total": total,
    }


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


@router.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: str, body: TodoUpdate, db: DbSession) -> JSONResponse | Todo:
    """Full replacement of a todo item."""
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

    title = body.title.strip()

    if not title:
        return JSONResponse(
            status_code=422,
            content={"detail": "title must not be blank"},
        )

    if len(title) > 500:
        return JSONResponse(
            status_code=422,
            content={"detail": "title must be 500 characters or fewer"},
        )

    # Check uniqueness excluding self
    existing = (
        db.query(Todo)
        .filter(Todo.title == title, Todo.id != id_int)
        .first()
    )
    if existing is not None:
        return JSONResponse(
            status_code=409,
            content={"detail": "A todo with this title already exists"},
        )

    todo.title = title
    todo.completed = body.completed
    db.commit()
    db.refresh(todo)
    return todo


@router.post("/todos/{todo_id}/complete", response_model=TodoResponse)
def complete_todo(todo_id: str, db: DbSession) -> JSONResponse | Todo:
    """Set a todo's completed status to true."""
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

    todo.completed = True
    db.commit()
    db.refresh(todo)
    return todo


@router.post("/todos/{todo_id}/incomplete", response_model=TodoResponse)
def incomplete_todo(todo_id: str, db: DbSession) -> JSONResponse | Todo:
    """Set a todo's completed status to false."""
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

    todo.completed = False
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/todos/{todo_id}", response_model=None)
def delete_todo(todo_id: str, db: DbSession) -> JSONResponse | Response:
    """Delete a todo item permanently."""
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

    db.delete(todo)
    db.commit()
    return Response(status_code=204)


@router.patch("/todos/{todo_id}", response_model=TodoResponse)
def patch_todo(todo_id: str, body: TodoPatch, db: DbSession) -> JSONResponse | Todo:
    """Partial update of a todo item."""
    id_int = _validate_todo_id(todo_id)
    if id_int is None:
        return JSONResponse(
            status_code=422,
            content={"detail": "id must be a positive integer"},
        )

    # Check that at least one recognized field is provided
    recognized_fields = body.model_fields_set & {"title", "completed"}
    if not recognized_fields:
        return JSONResponse(
            status_code=422,
            content={"detail": "At least one field must be provided"},
        )

    todo = db.query(Todo).filter(Todo.id == id_int).first()
    if todo is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "Todo not found"},
        )

    if "title" in recognized_fields:
        title = body.title.strip()  # type: ignore[union-attr]

        if not title:
            return JSONResponse(
                status_code=422,
                content={"detail": "title must not be blank"},
            )

        if len(title) > 500:
            return JSONResponse(
                status_code=422,
                content={"detail": "title must be 500 characters or fewer"},
            )

        # Check uniqueness excluding self
        existing = (
            db.query(Todo)
            .filter(Todo.title == title, Todo.id != id_int)
            .first()
        )
        if existing is not None:
            return JSONResponse(
                status_code=409,
                content={"detail": "A todo with this title already exists"},
            )

        todo.title = title

    if "completed" in recognized_fields:
        todo.completed = body.completed  # type: ignore[assignment]

    db.commit()
    db.refresh(todo)
    return todo
