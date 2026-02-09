"""FastAPI application entry point for the Todo API."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ralf_spike_2.database import init_db
from ralf_spike_2.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: create tables on startup."""
    await init_db()
    yield


app = FastAPI(title="Todo API", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Override default validation error to return single detail string."""
    errors = exc.errors()
    if errors:
        first = errors[0]
        msg = first.get("msg", "Validation error")
        return JSONResponse(
            status_code=422,
            content={"detail": msg},
        )
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error"},
    )
