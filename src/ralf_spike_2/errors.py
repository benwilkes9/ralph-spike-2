"""Error handling: validation helpers, custom exceptions, handlers."""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class TodoNotFoundError(HTTPException):
    """Raised when a todo with the given id does not exist."""

    def __init__(self) -> None:
        super().__init__(status_code=404, detail="Todo not found")


class DuplicateTitleError(HTTPException):
    """Raised when a todo with the same title already exists."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            detail="A todo with this title already exists",
        )


def validate_path_id(id: str) -> int:
    """Parse a path parameter as a positive integer.

    Raises HTTPException 422 if the value is not a positive integer.
    """
    try:
        value = int(id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422, detail="id must be a positive integer"
        ) from None
    if value <= 0:
        raise HTTPException(status_code=422, detail="id must be a positive integer")
    return value


def validate_title(title: str) -> str:
    """Trim whitespace and validate a title string.

    Returns the trimmed title on success.
    Raises HTTPException 422 if blank or exceeds 500 characters.
    """
    trimmed = title.strip()
    if not trimmed:
        raise HTTPException(status_code=422, detail="title must not be blank")
    if len(trimmed) > 500:
        raise HTTPException(
            status_code=422,
            detail="title must be 500 characters or fewer",
        )
    return trimmed


def _classify_validation_error(error: dict[str, object]) -> int:
    """Return a priority number for a validation error.

    Lower number = higher priority.
    Order: missing (1) -> type (2) -> value_error (3).
    """
    error_type = error.get("type", "")
    if error_type == "missing":
        return 1
    if error_type in (
        "string_type",
        "bool_type",
        "int_type",
        "type_error",
    ):
        return 2
    # value_error covers model validators like "at least one field"
    if error_type == "value_error":
        return 3
    return 2


def _format_validation_message(error: dict[str, object]) -> str:
    """Convert a Pydantic validation error to a user-friendly message."""
    error_type = error.get("type", "")
    raw_loc = error.get("loc", ())
    loc: list[str | int] = (
        list(raw_loc)  # type: ignore[arg-type]
        if isinstance(raw_loc, list | tuple)
        else []
    )

    # Determine the field name from location
    field_parts = [str(p) for p in loc if p != "body"]
    field_name = field_parts[-1] if field_parts else "field"

    if error_type == "missing":
        return f"{field_name} is required"
    if error_type in (
        "string_type",
        "bool_type",
        "int_type",
        "type_error",
    ):
        msg = error.get("msg", "")
        assert isinstance(msg, str)
        if msg:
            return f"{field_name}: {msg}"
        return f"{field_name} has an invalid type"
    if error_type == "value_error":
        msg = error.get("msg", "")
        assert isinstance(msg, str)
        # Strip Pydantic's "Value error, " prefix
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        return msg
    # Fallback
    msg = error.get("msg", "Validation error")
    assert isinstance(msg, str)
    return msg


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Override FastAPI's default validation error handler.

    Returns a single error message in {"detail": "..."} format,
    prioritised by validation order.
    """
    errors = exc.errors()
    if not errors:
        return JSONResponse(status_code=422, content={"detail": "Validation error"})
    # Sort by priority and pick the first
    sorted_errors = sorted(
        errors,
        key=lambda e: _classify_validation_error(e),  # type: ignore[arg-type]
    )
    first_error = sorted_errors[0]
    message = _format_validation_message(first_error)  # type: ignore[arg-type]
    return JSONResponse(status_code=422, content={"detail": message})
