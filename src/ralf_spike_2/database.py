"""Async SQLite database connection management."""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from fastapi import FastAPI

_DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///data/todos.db")


def _parse_db_path(url: str) -> str:
    """Convert DATABASE_URL to a filesystem path for aiosqlite."""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        path = url[len(prefix) :]
        if path == ":memory:":
            return ":memory:"
        return path
    return url


_db_path: str = _parse_db_path(_DATABASE_URL)

# Module-level connection for the running app
_connection: aiosqlite.Connection | None = None


async def get_connection() -> aiosqlite.Connection:
    """Return the active database connection."""
    if _connection is None:
        msg = "Database not initialized. Call init_db() first."
        raise RuntimeError(msg)
    return _connection


async def init_db(db_path: str | None = None) -> aiosqlite.Connection:
    """Initialize the database and create tables."""
    global _connection, _db_path
    if db_path is not None:
        _db_path = db_path
    _connection = await aiosqlite.connect(_db_path)
    _connection.row_factory = sqlite3.Row
    await _connection.execute("PRAGMA journal_mode=WAL")
    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT 0
        )
        """
    )
    await _connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_todos_title_nocase
        ON todos (title COLLATE NOCASE)
        """
    )
    await _connection.commit()
    return _connection


async def close_db() -> None:
    """Close the database connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager for database setup/teardown."""
    await init_db()
    yield
    await close_db()


@asynccontextmanager
async def test_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Context manager for in-memory test databases."""
    conn = await init_db(":memory:")
    try:
        yield conn
    finally:
        await close_db()
