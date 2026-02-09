# Implementation Plan: Todo CRUD REST API

All sections implemented and tested. 261 tests passing, pyright strict clean, ruff clean.

## Completed

All CRUD endpoints (1.x–6.x), error handling (5.x), filtering/sorting/pagination (4.x), and test hardening (0.0.9–0.0.13) are complete. See git history for details.

## Structured Logging (0.0.14)

- **Spec**: `specs/logging.md` — structured JSON request/response logging via ASGI middleware.
- **Implementation**: `src/ralf_spike_2/logging_middleware.py` — `LoggingMiddleware` (ASGI) + `_JsonFormatter` + `setup_logging()`.
- **Integration**: Middleware added in `main.py` via `app.add_middleware(LoggingMiddleware)`. Logger configured during app lifespan startup.
- **Log fields**: `method`, `path`, `query_string`, `status_code`, `duration_ms` — emitted as JSON at INFO level via `todo_api` logger.
- **Tests (23)**: `tests/test_logging.py` — covers all 9 acceptance criteria: log entry per request, all fields present, non-negative duration, status code accuracy (200/201/204/404/409/422), method/path correctness for all HTTP methods, query string handling, logger name, JSON format validity, no alteration of existing behavior.
- **Why ASGI middleware**: Wraps the entire app including exception handlers, so even error responses are logged. `BaseHTTPMiddleware` would also work but raw ASGI is more lightweight.
- **pyright note**: `record.msg` is typed as `str` but we pass dicts at runtime; use `cast("dict[str, Any]", msg)` after `isinstance` check.
- **Total: 23 new tests**, bringing count from 238 to 261.

## Architecture Notes

- **PUT/PATCH field tracking**: Both handlers use raw body dict inspection rather than Pydantic model validators because `extra="ignore"` strips tracking fields. Route handlers check `"title" in body` and `"completed" in body` directly. This ensures consistent null handling (null ≠ omitted).
- **Path param validation**: All `{todo_id}` params are typed as `str` to bypass FastAPI's built-in int conversion, enabling custom validation with consistent error messages.
- **Ruff config**: B008 suppressed for routes.py (FastAPI Depends pattern), TCH suppressed for test files (pytest fixture type hints need runtime imports).
- **SQLite AUTOINCREMENT**: Model uses `sqlite_autoincrement=True` in `__table_args__` to ensure deleted IDs are never reused per spec.
- **Cross-field validation**: PUT/PATCH validate type errors on all fields (title and completed) before blank/length on title. This matches the spec's priority ordering: missing(1) → type(2) → blank(3) → length(4) → uniqueness(5).
- **Search LIKE escaping**: The `\` character is used as the escape character in `ilike()` calls, with `%`, `_`, and `\` all properly escaped in search input.
- **JSON body validation**: `_parse_json_body` helper validates request body is a dict. `json.JSONDecodeError` handler in `main.py` catches malformed JSON. Both return 422 with `{"detail": "..."}`.
- **Path ID max value**: `_validate_path_id` rejects values > `2^63 - 1` to prevent SQLite OverflowError.
