# Implementation Plan: Todo CRUD REST API

All sections implemented and tested. 172 tests passing, pyright strict clean, ruff clean.

## Completed

- **1.1** Runtime dependencies (FastAPI, Uvicorn, SQLAlchemy[asyncio], aiosqlite, Pydantic) — [x]
- **1.2** Test dependencies (httpx, pytest-asyncio) — [x]
- **1.3** FastAPI app entry point (`src/ralf_spike_2/main.py`) with lifespan and router — [x]
- **2.1** SQLAlchemy Todo model with case-insensitive unique index on title — [x]
- **2.2** Async database connection (`src/ralf_spike_2/database.py`) with configurable DATABASE_URL — [x]
- **2.3** Test fixtures (`tests/conftest.py`) with async in-memory SQLite — [x]
- **3.1** POST /todos — create with validation, whitespace trim, uniqueness — [x]
- **3.2** GET /todos and GET /todos/{id} — list and retrieve — [x]
- **3.3** PUT /todos/{id} — full replacement update — [x]
- **3.4** PATCH /todos/{id} — partial update with "at least one field" check — [x]
- **3.5** POST /todos/{id}/complete and /incomplete — idempotent status toggles — [x]
- **3.6** DELETE /todos/{id} — hard delete returning 204 — [x]
- **4.1** Filtering by completed status query param — [x]
- **4.2** Case-insensitive title substring search — [x]
- **4.3** Sorting by id or title, asc or desc — [x]
- **4.4** Pagination with page/per_page — [x]
- **4.5** Response envelope (paginated) vs plain array (no params) — [x]
- **5.1** Consistent `{"detail": "..."}` error format — [x]
- **5.2** Validation ordering: missing → type → blank → length → uniqueness — [x]
- **5.3** Unknown field handling (silently ignored, PATCH "at least one" check) — [x]
- **5.4** Type mismatch handling for body fields and path params — [x]
- **5.5** Path parameter validation (positive integer, consistent across endpoints) — [x]
- **6.1** README updated with description, run instructions, endpoints table — [x]
- **6.2** pyproject.toml description updated — [x]
- **6.3** Package docstring updated — [x]

## Fixes Applied (0.0.9)

- **SQL LIKE wildcard escaping**: Search parameter now escapes `%`, `_`, and `\` before using `ilike()`, preventing SQL wildcard injection in substring search. Spec says "substring match", not "LIKE pattern match".
- **Cross-field validation ordering**: PUT and PATCH now check type errors across ALL fields (priority 2) before checking blank/length on any field (priority 3-4). Previously, title blank error (priority 3) was returned before completed type error (priority 2) when both were present.
- **Removed unused `_validate_completed_value` helper**: Inlined completed type checks into PUT/PATCH for correct cross-field ordering.
- **New tests (13)**: Case-insensitive title sorting (asc/desc), default sort in paginated responses, page 2 pagination, beyond-total page echoes requested page, LIKE wildcard escaping (% and _), POST completed non-boolean ignored, PUT empty body, completed-as-integer rejected (PUT/PATCH), cross-field validation order (PUT/PATCH), POST title:null exact message, complete/incomplete response shape.
- **Tightened existing tests**: complete/incomplete endpoint tests now verify full response shape (id, title, completed). POST title:null test now asserts exact error message.

## Fixes Applied (0.0.10)

- **Invalid JSON body handling**: POST/PUT/PATCH now return 422 with `{"detail": "..."}` for malformed JSON bodies (previously unhandled 500). Added `json.JSONDecodeError` exception handler in `main.py` and `_parse_json_body` helper in routes to validate body is a JSON object.
- **Non-object JSON body handling**: JSON arrays, strings, numbers, null as request body now return 422 `"Request body must be a JSON object"` instead of crashing with Pydantic validation error.
- **Very large path IDs**: Path IDs exceeding SQLite's INTEGER range (`2^63 - 1`) now return 422 instead of causing `OverflowError`. Added max value check in `_validate_path_id`.
- **PUT `completed: null` consistency**: PUT with `completed: null` now returns 422 `"completed must be a boolean"`, consistent with PATCH behavior. Previously silently treated null as omitted (defaulting to false).
- **PUT handler uses raw body directly**: Removed dependency on `TodoUpdate` Pydantic schema; PUT now validates directly from raw body dict like PATCH, ensuring consistent null/type handling.
- **Removed unused `TodoUpdate` schema**: No longer needed since PUT validates raw body directly.
- **New tests (23)**: Invalid JSON body (POST/PUT/PATCH), non-object JSON body (POST/PUT/PATCH), very large path IDs (GET/DELETE), PUT completed:null returns 422, response shape validation, missing title priority over bad completed, backslash in search, sort/order defaults, combined filter+sort+paginate, double-delete returns 404, interior whitespace preserved, float ID validation across all endpoints.

## Architecture Notes

- **PUT/PATCH field tracking**: Both handlers use raw body dict inspection rather than Pydantic model validators because `extra="ignore"` strips tracking fields. Route handlers check `"title" in body` and `"completed" in body` directly. This ensures consistent null handling (null ≠ omitted).
- **Path param validation**: All `{todo_id}` params are typed as `str` to bypass FastAPI's built-in int conversion, enabling custom validation with consistent error messages.
- **Ruff config**: B008 suppressed for routes.py (FastAPI Depends pattern), TCH suppressed for test files (pytest fixture type hints need runtime imports).
- **SQLite AUTOINCREMENT**: Model uses `sqlite_autoincrement=True` in `__table_args__` to ensure deleted IDs are never reused per spec.
- **Cross-field validation**: PUT/PATCH validate type errors on all fields (title and completed) before blank/length on title. This matches the spec's priority ordering: missing(1) → type(2) → blank(3) → length(4) → uniqueness(5).
- **Search LIKE escaping**: The `\` character is used as the escape character in `ilike()` calls, with `%`, `_`, and `\` all properly escaped in search input.
- **JSON body validation**: `_parse_json_body` helper validates request body is a dict. `json.JSONDecodeError` handler in `main.py` catches malformed JSON. Both return 422 with `{"detail": "..."}`.
- **Path ID max value**: `_validate_path_id` rejects values > `2^63 - 1` to prevent SQLite OverflowError.
