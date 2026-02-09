"""FastAPI application entry point with lifespan and health endpoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from ralf_spike_2.database import create_engine, create_session_factory, create_tables

engine = create_engine()
session_factory = create_session_factory(engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create database tables on startup."""
    await create_tables(engine)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async with session_factory() as session:
        yield session


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
