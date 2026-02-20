"""Shared test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from ralf_spike_2.app import app
from ralf_spike_2.database import Base, get_db

# In-memory SQLite engine for testing — StaticPool shares a single connection
# across threads, which is needed because TestClient runs in a separate thread.
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_test_engine, "connect")
def _set_sqlite_pragma(
    dbapi_connection: Any, _connection_record: Any
) -> None:
    cursor: Any = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


_TestSessionLocal = sessionmaker(bind=_test_engine)


@pytest.fixture(autouse=True)
def _setup_db() -> Generator[None, None, None]:
    """Create all tables before each test and drop after."""
    import ralf_spike_2.models  # noqa: F401  # pyright: ignore[reportUnusedImport]

    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


def _override_get_db() -> Generator[Session, None, None]:
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Test client with lifespan events and overridden DB."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
