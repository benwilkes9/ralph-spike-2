"""Shared test fixtures for the Todo CRUD API."""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from ralf_spike_2.app import app
from ralf_spike_2.database import create_engine, create_session_factory, create_tables
from ralf_spike_2.models import Base
from ralf_spike_2.routes import get_db_stub

IN_MEMORY_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create an in-memory async engine with tables."""
    eng = create_engine(IN_MEMORY_URL)
    await create_tables(eng)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield an async session bound to the in-memory engine."""
    factory = create_session_factory(test_engine)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """HTTP test client with in-memory database."""
    factory = create_session_factory(test_engine)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_stub] = _override_get_db
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db_stub, None)


@pytest_asyncio.fixture
async def clean_db(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """Ensure tables are fresh (drop and recreate)."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
