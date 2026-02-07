"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ralf_spike_2 import database as db
from ralf_spike_2.routes import HTTPError, router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the database on startup."""
    db.init_db()
    yield
    db.close_connection()


app = FastAPI(title="Todo CRUD API", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(HTTPError)
async def http_error_handler(
    request: Request,
    exc: HTTPError,
) -> JSONResponse:
    """Handle custom HTTP errors with {detail: string} format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Override FastAPI's default 422 to use simple {detail} format."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error"},
    )
