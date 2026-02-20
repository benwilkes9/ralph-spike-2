"""Tests for Task 2: Database Layer & Todo Model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ralf_spike_2.database import Base
from ralf_spike_2.models import Todo


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database for testing."""
    test_engine = create_engine("sqlite:///:memory:")

    @event.listens_for(test_engine, "connect")
    def _set_sqlite_pragma(
        dbapi_connection: Any, _connection_record: Any
    ) -> None:
        cursor: Any = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine)()
    try:
        yield test_session
    finally:
        test_session.close()


def test_todo_insert_and_retrieve(db: Session) -> None:
    """A Todo record can be inserted and retrieved from the database."""
    todo = Todo(title="Buy milk")
    db.add(todo)
    db.commit()
    db.refresh(todo)

    retrieved = db.get(Todo, todo.id)
    assert retrieved is not None
    assert retrieved.title == "Buy milk"
    assert retrieved.completed is False


def test_id_auto_generated(db: Session) -> None:
    """id is auto-generated as an incrementing integer."""
    todo1 = Todo(title="First")
    todo2 = Todo(title="Second")
    db.add(todo1)
    db.commit()
    db.add(todo2)
    db.commit()

    db.refresh(todo1)
    db.refresh(todo2)
    assert isinstance(todo1.id, int)
    assert isinstance(todo2.id, int)
    assert todo2.id > todo1.id


def test_completed_defaults_to_false(db: Session) -> None:
    """completed defaults to false when not specified."""
    todo = Todo(title="Test default")
    db.add(todo)
    db.commit()
    db.refresh(todo)

    assert todo.completed is False


def test_case_insensitive_uniqueness(db: Session) -> None:
    """Inserting two todos with titles differing only by case raises
    a uniqueness violation at the DB level."""
    todo1 = Todo(title="Buy milk")
    db.add(todo1)
    db.commit()

    todo2 = Todo(title="buy milk")
    db.add(todo2)
    with pytest.raises(IntegrityError):
        db.commit()


def test_title_stored_as_provided(db: Session) -> None:
    """title is stored as provided (trimming is an application concern, not DB)."""
    todo = Todo(title="  hello world  ")
    db.add(todo)
    db.commit()
    db.refresh(todo)

    assert todo.title == "  hello world  "


def test_deleted_ids_never_reused(db: Session) -> None:
    """Deleted id values are never reused (SQLite auto-increment behavior)."""
    todo1 = Todo(title="First")
    db.add(todo1)
    db.commit()
    db.refresh(todo1)
    first_id = todo1.id

    db.delete(todo1)
    db.commit()

    todo2 = Todo(title="Second")
    db.add(todo2)
    db.commit()
    db.refresh(todo2)

    assert todo2.id > first_id
