"""Tests for the database layer: engine, session, table creation, and TodoModel."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import Connection, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from ralf_spike_2.database import create_engine, create_session_factory, create_tables
from ralf_spike_2.models import TodoModel

IN_MEMORY_URL = "sqlite+aiosqlite:///:memory:"


def _get_table_names(sync_conn: Connection) -> list[str]:
    return inspect(sync_conn).get_table_names()


def _get_columns(sync_conn: Connection) -> dict[str, Any]:
    return {c["name"]: c for c in inspect(sync_conn).get_columns("todos")}


def _get_pk_constraint(sync_conn: Connection) -> dict[str, Any]:
    return inspect(sync_conn).get_pk_constraint("todos")  # type: ignore[return-value]


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Create an async in-memory engine and yield it."""
    eng = create_engine(IN_MEMORY_URL)
    await create_tables(eng)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Create an async session bound to the in-memory engine."""
    factory = create_session_factory(engine)
    async with factory() as sess:
        yield sess


@pytest.mark.asyncio
async def test_create_tables_succeeds() -> None:
    """Creating tables on an in-memory SQLite database succeeds."""
    eng = create_engine(IN_MEMORY_URL)
    await create_tables(eng)

    async with eng.connect() as conn:
        table_names = await conn.run_sync(_get_table_names)
    assert "todos" in table_names
    await eng.dispose()


@pytest.mark.asyncio
async def test_todo_model_column_types(engine: AsyncEngine) -> None:
    """TodoModel has the correct column types and constraints."""
    async with engine.connect() as conn:
        columns = await conn.run_sync(_get_columns)
        pk_info = await conn.run_sync(_get_pk_constraint)

    assert "id" in columns
    assert "title" in columns
    assert "title_lower" in columns
    assert "completed" in columns

    # id is primary key
    assert "id" in pk_info["constrained_columns"]

    # title is not nullable
    assert columns["title"]["nullable"] is False

    # title_lower is not nullable
    assert columns["title_lower"]["nullable"] is False

    # completed is not nullable and has a default
    assert columns["completed"]["nullable"] is False


@pytest.mark.asyncio
async def test_insert_valid_row_autogenerates_id(session: AsyncSession) -> None:
    """Inserting a row with valid data succeeds and auto-generates an id."""
    todo = TodoModel(title="Buy milk", title_lower="buy milk", completed=False)
    session.add(todo)
    await session.commit()
    await session.refresh(todo)

    assert todo.id is not None
    assert todo.id > 0
    assert todo.title == "Buy milk"
    assert todo.title_lower == "buy milk"
    assert todo.completed is False


@pytest.mark.asyncio
async def test_title_lower_unique_constraint(session: AsyncSession) -> None:
    """Inserting two rows with title_lower collisions raises IntegrityError."""
    todo1 = TodoModel(title="Buy milk", title_lower="buy milk", completed=False)
    session.add(todo1)
    await session.commit()

    todo2 = TodoModel(title="BUY MILK", title_lower="buy milk", completed=False)
    session.add(todo2)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_completed_defaults_to_false(session: AsyncSession) -> None:
    """completed defaults to false when not provided."""
    todo = TodoModel(title="Test task", title_lower="test task")
    session.add(todo)
    await session.commit()
    await session.refresh(todo)

    assert todo.completed is False


@pytest.mark.asyncio
async def test_title_longer_than_500_can_be_stored(session: AsyncSession) -> None:
    """Title longer than 500 characters can be stored at the DB level.

    SQLite does not enforce string length constraints, so validation
    is the responsibility of the application layer.
    """
    long_title = "a" * 501
    todo = TodoModel(title=long_title, title_lower=long_title.lower(), completed=False)
    session.add(todo)
    await session.commit()
    await session.refresh(todo)

    assert len(todo.title) == 501
