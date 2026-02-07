"""Tests for database layer (Task 2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def test_table_created_with_correct_schema(db: aiosqlite.Connection) -> None:
    """Database table is created on startup with correct schema."""
    cursor = await db.execute("PRAGMA table_info(todos)")
    columns = await cursor.fetchall()
    col_names = [col[1] for col in columns]
    assert "id" in col_names
    assert "title" in col_names
    assert "completed" in col_names


async def test_in_memory_database_works(db: aiosqlite.Connection) -> None:
    """In-memory database works for testing."""
    await db.execute("INSERT INTO todos (title) VALUES ('test')")
    await db.commit()
    cursor = await db.execute("SELECT COUNT(*) FROM todos")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 1


async def test_unique_index_on_title(db: aiosqlite.Connection) -> None:
    """Case-insensitive unique index prevents duplicate titles."""
    await db.execute("INSERT INTO todos (title) VALUES ('Buy milk')")
    await db.commit()
    import sqlite3

    with __import__("pytest").raises(sqlite3.IntegrityError):
        await db.execute("INSERT INTO todos (title) VALUES ('buy milk')")
        await db.commit()
