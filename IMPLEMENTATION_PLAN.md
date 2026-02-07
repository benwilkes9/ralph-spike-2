# Implementation Plan

## Task 1: Project dependencies and configuration
- Add FastAPI, uvicorn, and aiosqlite to `pyproject.toml` dependencies
- Add httpx to dev dependencies (for `TestClient` / async test support)
- Update `README.md` with project description, how to run the app, and API overview so a new developer can clone and run
- **Tests:**
  - `uv sync --all-extras` succeeds without errors
  - `uv run python -c "import fastapi; import aiosqlite"` succeeds

## Task 2: Database layer (SQLite + model)
- Create `src/ralf_spike_2/database.py` — async SQLite connection management using aiosqlite
  - Use `DATABASE_URL` env var (default `sqlite:///data/todos.db`; tests use `sqlite:///:memory:`)
  - Create `todos` table on startup: `id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, completed BOOLEAN NOT NULL DEFAULT 0`
  - Add case-insensitive unique index on `title` (using `COLLATE NOCASE` or `LOWER(title)`)
- Create `src/ralf_spike_2/models.py` — Pydantic schemas for request/response
  - `TodoCreate`: title (str, required)
  - `TodoUpdate` (PUT): title (str, required), completed (bool, optional, default false)
  - `TodoPatch`: title (str | None), completed (bool | None) — at least one required
  - `TodoResponse`: id (int), title (str), completed (bool)
  - `PaginatedResponse`: items (list[TodoResponse]), page (int), per_page (int), total (int)
- **Tests:**
  - Database table is created on startup with correct schema
  - In-memory database works for testing
  - Pydantic models validate correctly (accept valid, reject invalid)

## Task 3: Create a Todo — `POST /todos`
- Create `src/ralf_spike_2/main.py` — FastAPI app instance with the POST endpoint
- Create `src/ralf_spike_2/routes.py` (or keep in main.py) — route handlers
- Implement `POST /todos`:
  - Trim title whitespace before validation
  - Validate: required, non-blank, max 500 chars
  - Check case-insensitive uniqueness → 409 if duplicate
  - Return 201 with `{id, title, completed}` on success
  - `completed` always false on creation; ignore `completed` if sent in body
  - Silently ignore unknown fields
- **Tests:**
  - Valid POST creates todo → 201, returns `{id, title, completed: false}`
  - Returned `id` is auto-generated integer
  - `completed` is always false on creation
  - Missing title → 422 `{"detail": "title is required"}`
  - Empty string title → 422 `{"detail": "title must not be blank"}`
  - Whitespace-only title → 422 `{"detail": "title must not be blank"}`
  - Title > 500 chars → 422 `{"detail": "title must be 500 characters or fewer"}`
  - Duplicate title (case-insensitive) → 409 `{"detail": "A todo with this title already exists"}`
  - Leading/trailing whitespace is trimmed in stored title
  - Unknown fields in body are silently ignored

## Task 4: Retrieve Todos — `GET /todos` and `GET /todos/{id}`
- `GET /todos` — return all todos as plain JSON array, ordered by `id` descending (newest first)
- `GET /todos/{id}` — return single todo by id
- Validate `id` is a positive integer → 422 if not
- Return 404 if id not found
- Error responses use `{"detail": "..."}` format
- **Tests:**
  - `GET /todos` returns 200 with all todos, newest first (descending id)
  - `GET /todos` returns 200 with `[]` when no todos exist
  - `GET /todos/{id}` returns 200 with matching todo
  - `GET /todos/{id}` with non-existent id → 404 `{"detail": "Todo not found"}`
  - `GET /todos/{id}` with non-integer id (e.g., "abc") → 422 `{"detail": "id must be a positive integer"}`
  - `GET /todos/{id}` with negative/zero id → 422

## Task 5: Update a Todo — `PUT /todos/{id}`
- Full replacement: title required, completed optional (defaults to false if omitted)
- Trim title, validate same rules as create
- Uniqueness check excludes the todo being updated
- Return 200 with updated todo
- **Tests:**
  - PUT replaces title and completed → 200
  - Omitting `completed` resets it to false
  - Missing title → 422
  - Blank/whitespace title → 422
  - Title > 500 chars → 422
  - Duplicate title (different todo) → 409
  - Non-existent id → 404
  - Non-integer id → 422
  - Title is trimmed on update
  - Unknown fields silently ignored

## Task 6: Partial Update — `PATCH /todos/{id}`
- Only provided fields updated; omitted fields unchanged
- At least one recognised field required → 422 if empty or only unknown fields
- Same validation rules for title when provided
- Return 200 with updated todo
- **Tests:**
  - PATCH updates only provided fields
  - PATCH title only — completed unchanged
  - PATCH completed only — title unchanged
  - PATCH with no fields → 422 `{"detail": "At least one field must be provided"}`
  - PATCH with only unknown fields → 422
  - Blank/whitespace title → 422
  - Duplicate title → 409
  - Non-existent id → 404
  - Non-integer id → 422

## Task 7: Convenience endpoints — `POST /todos/{id}/complete` and `/incomplete`
- `POST /todos/{id}/complete` — sets completed to true, idempotent
- `POST /todos/{id}/incomplete` — sets completed to false, idempotent
- No request body required
- Return 200 with updated todo
- **Tests:**
  - `/complete` sets completed to true → 200
  - `/complete` on already-complete todo succeeds (idempotent)
  - `/incomplete` sets completed to false → 200
  - `/incomplete` on already-incomplete todo succeeds (idempotent)
  - Non-existent id → 404
  - Non-integer id → 422

## Task 8: Delete a Todo — `DELETE /todos/{id}`
- Hard delete, return 204 No Content (empty body)
- Validate id is positive integer
- Return 404 if not found
- **Tests:**
  - Delete existing todo → 204, empty body
  - Todo is no longer retrievable after deletion
  - Delete non-existent id → 404
  - Delete with non-integer id → 422

## Task 9: List filtering, sorting, search, and pagination — `GET /todos` query params
- Query params: `completed`, `search`, `sort`, `order`, `page`, `per_page`
- When any query param is provided, wrap response in pagination envelope `{items, page, per_page, total}`
- When no query params, return plain JSON array (backward compatible)
- Filtering: `completed=true|false`; invalid values → 422
- Search: case-insensitive substring match on title; empty string = no filter
- Sorting: `sort=id|title`, `order=asc|desc`; defaults `id` / `desc`
- Pagination: `page` >= 1, `per_page` 1–100; defaults 1 / 10
- Page beyond last returns empty items with correct total
- **Tests:**
  - `?completed=true` returns only completed todos
  - `?completed=false` returns only incomplete todos
  - `?completed=invalid` → 422
  - `?search=buy` returns todos with "buy" in title (case-insensitive)
  - Empty search string returns all
  - Search + filter combined
  - `?sort=title&order=asc` sorts alphabetically ascending (case-insensitive)
  - `?sort=id&order=desc` is default behavior
  - Invalid sort value → 422
  - Invalid order value → 422
  - Paginated response includes `items`, `page`, `per_page`, `total`
  - Page beyond total → empty items, correct total
  - `per_page=1` returns one item
  - `page=0` → 422
  - `per_page=0` → 422
  - `per_page=101` → 422
  - No query params → plain JSON array (backward compatible)

## Task 10: Error handling consistency
- All error responses use `{"detail": "..."}` format
- Override FastAPI's default 422 handler for RequestValidationError to return single `{"detail": "..."}` messages
- Custom exception handlers for 404, 409, 422
- Validation order: missing → type/format → blank → length → uniqueness
- Type mismatches on recognised fields → 422
- **Tests:**
  - All error responses use `{"detail": "..."}` format (not FastAPI's default array format)
  - Only one error returned per request
  - Validation errors → 422
  - Uniqueness violations → 409
  - Missing resources → 404
  - Type mismatches (e.g., `title: 123`, `completed: "yes"`) → 422

## Task 11: README and documentation update
- Update `README.md` with:
  - Project description (Todo API)
  - How to install dependencies
  - How to run the app (`DATABASE_URL=... uv run uvicorn ralf_spike_2.main:app`)
  - API endpoint summary
  - How to run tests
- **Tests:** N/A (manual verification)
