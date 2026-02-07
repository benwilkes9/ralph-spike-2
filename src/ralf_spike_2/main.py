"""FastAPI Todo application."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ralf_spike_2.database import lifespan
from ralf_spike_2.routes import router

app = FastAPI(title="Todo API", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return single error message instead of FastAPI's default array format."""
    errors = list(exc.errors())
    if errors:
        error = errors[0]
        loc: tuple[str | int, ...] = tuple(error.get("loc", ()))
        error_type: str = error.get("type", "")
        msg: str = error.get("msg", "Validation error")

        # Path parameter validation (e.g., /todos/{id})
        if len(loc) >= 2 and loc[0] == "path":
            field = str(loc[1])
            if field == "id":
                return JSONResponse(
                    status_code=422,
                    content={"detail": "id must be a positive integer"},
                )

        # Body field validation
        if len(loc) >= 2 and loc[0] == "body":
            field = str(loc[1])
            if error_type == "missing":
                return JSONResponse(
                    status_code=422,
                    content={"detail": f"{field} is required"},
                )
            # Type errors on recognized fields
            return JSONResponse(
                status_code=422,
                content={"detail": f"{field} {msg}"},
            )

        # Fallback for body-level errors (e.g., invalid JSON)
        if len(loc) >= 1 and loc[0] == "body":
            return JSONResponse(
                status_code=422,
                content={"detail": msg},
            )

    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error"},
    )
