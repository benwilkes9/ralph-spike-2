"""Route handlers for the Todo API."""

from __future__ import annotations

from typing import Any

import aiosqlite  # noqa: TC002
from fastapi import APIRouter, Path, Query, Request, Response
from fastapi.responses import JSONResponse

from ralf_spike_2.database import get_connection
from ralf_spike_2.models import (  # noqa: TC001
    TodoCreate,
    TodoPatch,
    TodoUpdate,
)

router = APIRouter()


def _validate_title(title: str) -> tuple[str, JSONResponse | None]:
    """Validate and trim a title. Returns (trimmed_title, error_response)."""
    trimmed = title.strip()
    if not trimmed:
        return trimmed, JSONResponse(
            status_code=422,
            content={"detail": "title must not be blank"},
        )
    if len(trimmed) > 500:
        return trimmed, JSONResponse(
            status_code=422,
            content={"detail": "title must be 500 characters or fewer"},
        )
    return trimmed, None


async def _check_title_unique(
    db: aiosqlite.Connection, title: str, exclude_id: int | None = None
) -> JSONResponse | None:
    """Check case-insensitive title uniqueness. Returns error or None."""
    if exclude_id is not None:
        cursor = await db.execute(
            "SELECT id FROM todos WHERE title = ?1 COLLATE NOCASE AND id != ?2",
            (title, exclude_id),
        )
    else:
        cursor = await db.execute(
            "SELECT id FROM todos WHERE title = ?1 COLLATE NOCASE",
            (title,),
        )
    row = await cursor.fetchone()
    if row is not None:
        return JSONResponse(
            status_code=409,
            content={"detail": "A todo with this title already exists"},
        )
    return None


async def _get_todo_or_404(
    db: aiosqlite.Connection, todo_id: int
) -> tuple[dict[str, Any] | None, JSONResponse | None]:
    """Fetch a todo by id. Returns (todo_dict, error_response)."""
    if todo_id < 1:
        return None, JSONResponse(
            status_code=422,
            content={"detail": "id must be a positive integer"},
        )
    cursor = await db.execute(
        "SELECT id, title, completed FROM todos WHERE id = ?", (todo_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None, JSONResponse(
            status_code=404,
            content={"detail": "Todo not found"},
        )
    return {"id": row[0], "title": row[1], "completed": bool(row[2])}, None


@router.post("/todos", status_code=201, response_model=None)
async def create_todo(body: TodoCreate) -> JSONResponse:
    """Create a new todo."""
    title, error = _validate_title(body.title)
    if error:
        return error

    db = await get_connection()
    dup_error = await _check_title_unique(db, title)
    if dup_error:
        return dup_error

    cursor = await db.execute(
        "INSERT INTO todos (title, completed) VALUES (?, 0)", (title,)
    )
    await db.commit()
    todo_id = cursor.lastrowid

    return JSONResponse(
        status_code=201,
        content={"id": todo_id, "title": title, "completed": False},
    )


@router.get("/todos", response_model=None)
async def list_todos(
    request: Request,
    completed: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
    page: str | None = Query(default=None),
    per_page: str | None = Query(default=None),
) -> JSONResponse:
    """List todos with optional filtering, sorting, search, and pagination."""
    has_query_params = bool(request.query_params)

    # Validate query params
    completed_filter: bool | None = None
    if completed is not None:
        if completed not in ("true", "false"):
            return JSONResponse(
                status_code=422,
                content={"detail": "completed must be true or false"},
            )
        completed_filter = completed == "true"

    sort_field = "id"
    if sort is not None:
        if sort not in ("id", "title"):
            return JSONResponse(
                status_code=422,
                content={"detail": "sort must be 'id' or 'title'"},
            )
        sort_field = sort

    order_dir = "desc"
    if order is not None:
        if order not in ("asc", "desc"):
            return JSONResponse(
                status_code=422,
                content={"detail": "order must be 'asc' or 'desc'"},
            )
        order_dir = order

    page_num = 1
    if page is not None:
        try:
            page_num = int(page)
        except ValueError:
            return JSONResponse(
                status_code=422,
                content={"detail": "page must be a positive integer"},
            )
        if page_num < 1:
            return JSONResponse(
                status_code=422,
                content={"detail": "page must be a positive integer"},
            )

    per_page_num = 10
    if per_page is not None:
        try:
            per_page_num = int(per_page)
        except ValueError:
            return JSONResponse(
                status_code=422,
                content={"detail": "per_page must be an integer between 1 and 100"},
            )
        if per_page_num < 1 or per_page_num > 100:
            return JSONResponse(
                status_code=422,
                content={"detail": "per_page must be an integer between 1 and 100"},
            )

    # Build query
    db = await get_connection()
    conditions: list[str] = []
    params: list[str | int | bool] = []

    if completed_filter is not None:
        conditions.append("completed = ?")
        params.append(completed_filter)

    if search is not None and search != "":
        conditions.append("title LIKE ?")
        params.append(f"%{search}%")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Sort
    if sort_field == "title":
        order_clause = f"ORDER BY title COLLATE NOCASE {order_dir.upper()}"
    else:
        order_clause = f"ORDER BY id {order_dir.upper()}"

    select = "SELECT id, title, completed FROM todos"
    select_q = f"{select} {where_clause} {order_clause}"

    if not has_query_params:
        # Plain array response
        cursor = await db.execute(select_q, params)
        rows = await cursor.fetchall()
        items = [
            {"id": row[0], "title": row[1], "completed": bool(row[2])} for row in rows
        ]
        return JSONResponse(content=items)

    # Paginated response
    count_q = f"SELECT COUNT(*) FROM todos {where_clause}"
    count_cursor = await db.execute(count_q, params)
    count_row = await count_cursor.fetchone()
    total = count_row[0] if count_row else 0

    offset = (page_num - 1) * per_page_num
    paged_q = f"{select_q} LIMIT ? OFFSET ?"
    cursor = await db.execute(
        paged_q,
        [*params, per_page_num, offset],
    )
    rows = await cursor.fetchall()
    items = [{"id": row[0], "title": row[1], "completed": bool(row[2])} for row in rows]

    return JSONResponse(
        content={
            "items": items,
            "page": page_num,
            "per_page": per_page_num,
            "total": total,
        }
    )


@router.get("/todos/{id}", response_model=None)
async def get_todo(id: int = Path(gt=0)) -> JSONResponse:
    """Get a single todo by id."""
    db = await get_connection()
    todo, error = await _get_todo_or_404(db, id)
    if error:
        return error
    assert todo is not None
    return JSONResponse(content=todo)


@router.put("/todos/{id}", response_model=None)
async def update_todo(body: TodoUpdate, id: int = Path(gt=0)) -> JSONResponse:
    """Full replacement of a todo."""
    db = await get_connection()
    todo, error = await _get_todo_or_404(db, id)
    if error:
        return error
    assert todo is not None

    title, val_error = _validate_title(body.title)
    if val_error:
        return val_error

    dup_error = await _check_title_unique(db, title, exclude_id=id)
    if dup_error:
        return dup_error

    completed = body.completed
    await db.execute(
        "UPDATE todos SET title = ?, completed = ? WHERE id = ?",
        (title, completed, id),
    )
    await db.commit()
    return JSONResponse(content={"id": id, "title": title, "completed": completed})


@router.patch("/todos/{id}", response_model=None)
async def patch_todo(body: TodoPatch, id: int = Path(gt=0)) -> JSONResponse:
    """Partial update of a todo."""
    if body.title is None and body.completed is None:
        return JSONResponse(
            status_code=422,
            content={"detail": "At least one field must be provided"},
        )

    db = await get_connection()
    todo, error = await _get_todo_or_404(db, id)
    if error:
        return error
    assert todo is not None

    new_title = todo["title"]
    new_completed = todo["completed"]

    if body.title is not None:
        new_title, val_error = _validate_title(body.title)
        if val_error:
            return val_error
        dup_error = await _check_title_unique(db, new_title, exclude_id=id)
        if dup_error:
            return dup_error

    if body.completed is not None:
        new_completed = body.completed

    await db.execute(
        "UPDATE todos SET title = ?, completed = ? WHERE id = ?",
        (new_title, new_completed, id),
    )
    await db.commit()
    return JSONResponse(
        content={"id": id, "title": new_title, "completed": new_completed}
    )


@router.post("/todos/{id}/complete", response_model=None)
async def complete_todo(id: int = Path(gt=0)) -> JSONResponse:
    """Mark a todo as complete."""
    db = await get_connection()
    todo, error = await _get_todo_or_404(db, id)
    if error:
        return error
    assert todo is not None

    await db.execute("UPDATE todos SET completed = 1 WHERE id = ?", (id,))
    await db.commit()
    return JSONResponse(content={"id": id, "title": todo["title"], "completed": True})


@router.post("/todos/{id}/incomplete", response_model=None)
async def incomplete_todo(id: int = Path(gt=0)) -> JSONResponse:
    """Mark a todo as incomplete."""
    db = await get_connection()
    todo, error = await _get_todo_or_404(db, id)
    if error:
        return error
    assert todo is not None

    await db.execute("UPDATE todos SET completed = 0 WHERE id = ?", (id,))
    await db.commit()
    return JSONResponse(content={"id": id, "title": todo["title"], "completed": False})


@router.delete("/todos/{id}", response_model=None)
async def delete_todo(id: int = Path(gt=0)) -> Response | JSONResponse:
    """Delete a todo."""
    db = await get_connection()
    todo, error = await _get_todo_or_404(db, id)
    if error:
        return error
    assert todo is not None

    await db.execute("DELETE FROM todos WHERE id = ?", (id,))
    await db.commit()
    return Response(status_code=204)
