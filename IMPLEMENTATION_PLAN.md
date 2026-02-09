# Implementation Plan: Todo CRUD REST API

All sections implemented and tested. 123 tests passing, pyright strict clean, ruff clean.

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

## Architecture Notes

- **PATCH field tracking**: Uses raw body dict inspection rather than Pydantic model validators because `extra="ignore"` strips tracking fields. The route handler checks `"title" in body` and `"completed" in body` directly.
- **Path param validation**: All `{todo_id}` params are typed as `str` to bypass FastAPI's built-in int conversion, enabling custom validation with consistent error messages.
- **Ruff config**: B008 suppressed for routes.py (FastAPI Depends pattern), TCH suppressed for test files (pytest fixture type hints need runtime imports).
