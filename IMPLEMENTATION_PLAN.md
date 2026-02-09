# Implementation Plan: Todo CRUD REST API

All sections implemented and tested. 136 tests passing, pyright strict clean, ruff clean.

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

## Fixes Applied (0.0.8)

- **Error messages aligned to spec**: Title length (`"title must be 500 characters or fewer"`), completed filter (`"completed must be true or false"` without quotes), per_page (`"per_page must be an integer between 1 and 100"` with "an integer").
- **PATCH `title: null`**: Changed from `"title is required"` to `"title must be a string"` — in PATCH, title is optional so null is a type error, not a missing field.
- **SQLite AUTOINCREMENT**: Added `sqlite_autoincrement=True` to Todo model to prevent ID reuse after deletion, matching spec requirement.
- **Test assertions tightened**: All error detail messages now use exact string equality assertions instead of loose substring checks. Covers create, update, delete, filtering, sorting, pagination.
- **New tests added (13)**: PATCH title null/non-string/completed null, PUT title null/non-string/completed string, deleted ID not reused, combined trim+case-fold uniqueness, title 500 after trim, per_page=100 boundary, empty DB pagination, page/per_page float strings.

## Architecture Notes

- **PATCH field tracking**: Uses raw body dict inspection rather than Pydantic model validators because `extra="ignore"` strips tracking fields. The route handler checks `"title" in body` and `"completed" in body` directly.
- **Path param validation**: All `{todo_id}` params are typed as `str` to bypass FastAPI's built-in int conversion, enabling custom validation with consistent error messages.
- **Ruff config**: B008 suppressed for routes.py (FastAPI Depends pattern), TCH suppressed for test files (pytest fixture type hints need runtime imports).
- **SQLite AUTOINCREMENT**: Model uses `sqlite_autoincrement=True` in `__table_args__` to ensure deleted IDs are never reused per spec.
