"""FastAPI application entry point."""

import json

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI()

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Override default 422 to return {"detail": "..."} as a string."""
        errors = exc.errors()
        if errors:
            err = errors[0]
            loc = err.get("loc", ())
            field = loc[-1] if loc else "value"
            err_type = err.get("type", "")

            if err_type == "json_invalid":
                detail = "Invalid JSON in request body"
            elif err_type == "missing":
                detail = f"{field} is required"
            elif err_type == "string_type":
                detail = f"{field} must be a string"
            elif err_type == "bool_type":
                detail = f"{field} must be a boolean"
            else:
                detail = err.get("msg", "Validation error")
        else:
            detail = "Validation error"

        return JSONResponse(
            status_code=422,
            content={"detail": detail},
        )

    @application.exception_handler(json.JSONDecodeError)
    async def json_decode_error_handler(
        request: Request, exc: json.JSONDecodeError
    ) -> JSONResponse:
        """Handle malformed JSON request bodies."""
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid JSON in request body"},
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Ensure all HTTP exceptions use {"detail": "..."} format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail)},
        )

    @application.get("/")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return application


app = create_app()
