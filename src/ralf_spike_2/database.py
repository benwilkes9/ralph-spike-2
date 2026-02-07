"""SQLite database layer for Todo CRUD API."""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any

_local = threading.local()

DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///todos.db")


def _parse_url(url: str) -> str:
    """Convert DATABASE_URL to a sqlite3 connect path."""
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///") :]
    if url.startswith("sqlite://"):
        return url[len("sqlite://") :]
    return url


def get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    conn: sqlite3.Connection | None = getattr(_local, "connection", None)
    if conn is None:
        path = _parse_url(DATABASE_URL)
        is_uri = path.startswith("file:")
        conn = sqlite3.connect(path, uri=is_uri)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.connection = conn
    return conn


def close_connection() -> None:
    """Close the thread-local database connection."""
    conn: sqlite3.Connection | None = getattr(_local, "connection", None)
    if conn is not None:
        conn.close()
        _local.connection = None


def init_db() -> None:
    """Create the todos table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL COLLATE NOCASE,
            completed BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_todos_title_nocase
        ON todos (title COLLATE NOCASE)
    """)
    conn.commit()


# --- CRUD operations ---


def create_todo(title: str) -> dict[str, Any]:
    """Insert a new todo and return it."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO todos (title, completed) VALUES (?, 0)",
        (title,),
    )
    conn.commit()
    todo_id = cursor.lastrowid
    row = conn.execute(
        "SELECT id, title, completed FROM todos WHERE id = ?",
        (todo_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_all_todos() -> list[dict[str, Any]]:
    """Return all todos ordered by id descending."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, completed FROM todos ORDER BY id DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_todo_by_id(todo_id: int) -> dict[str, Any] | None:
    """Return a single todo by id, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, title, completed FROM todos WHERE id = ?",
        (todo_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def update_todo(
    todo_id: int,
    title: str,
    completed: bool,
) -> dict[str, Any] | None:
    """Full update of a todo. Returns updated todo or None if not found."""
    conn = get_connection()
    conn.execute(
        "UPDATE todos SET title = ?, completed = ? WHERE id = ?",
        (title, int(completed), todo_id),
    )
    conn.commit()
    return get_todo_by_id(todo_id)


def patch_todo(
    todo_id: int,
    title: str | None = None,
    completed: bool | None = None,
) -> dict[str, Any] | None:
    """Partial update of a todo. Returns updated todo or None if not found."""
    conn = get_connection()
    parts: list[str] = []
    params: list[Any] = []
    if title is not None:
        parts.append("title = ?")
        params.append(title)
    if completed is not None:
        parts.append("completed = ?")
        params.append(int(completed))
    if not parts:
        return get_todo_by_id(todo_id)
    params.append(todo_id)
    sql = f"UPDATE todos SET {', '.join(parts)} WHERE id = ?"
    conn.execute(sql, params)
    conn.commit()
    return get_todo_by_id(todo_id)


def delete_todo(todo_id: int) -> bool:
    """Delete a todo. Returns True if deleted, False if not found."""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    return cursor.rowcount > 0


def check_title_unique(title: str, exclude_id: int | None = None) -> bool:
    """Check if title is unique (case-insensitive). Returns True if unique."""
    conn = get_connection()
    if exclude_id is not None:
        row = conn.execute(
            "SELECT id FROM todos WHERE title = ? COLLATE NOCASE AND id != ?",
            (title, exclude_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM todos WHERE title = ? COLLATE NOCASE",
            (title,),
        ).fetchone()
    return row is None


def query_todos(
    completed: bool | None = None,
    search: str | None = None,
    sort: str = "id",
    order: str = "desc",
    page: int = 1,
    per_page: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    """Query todos with filtering, search, sorting, pagination.

    Returns (items, total_count).
    """
    conn = get_connection()
    where_parts: list[str] = []
    params: list[Any] = []

    if completed is not None:
        where_parts.append("completed = ?")
        params.append(int(completed))

    if search:
        where_parts.append("title LIKE ?")
        params.append(f"%{search}%")

    where_clause = ""
    if where_parts:
        where_clause = "WHERE " + " AND ".join(where_parts)

    # Count total
    count_sql = f"SELECT COUNT(*) FROM todos {where_clause}"
    total: int = conn.execute(count_sql, params).fetchone()[0]

    # Sort
    order_col = "title COLLATE NOCASE" if sort == "title" else "id"
    order_dir = "ASC" if order == "asc" else "DESC"

    offset = (page - 1) * per_page
    query_sql = (
        f"SELECT id, title, completed FROM todos {where_clause} "
        f"ORDER BY {order_col} {order_dir} "
        f"LIMIT ? OFFSET ?"
    )
    rows = conn.execute(query_sql, [*params, per_page, offset]).fetchall()
    return [_row_to_dict(r) for r in rows], total


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    """Convert a sqlite3.Row to a dict with proper types."""
    if row is None:
        return {}
    return {
        "id": row["id"],
        "title": row["title"],
        "completed": bool(row["completed"]),
    }
