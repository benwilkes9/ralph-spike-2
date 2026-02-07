# Implementation Plan

## Current State

The project is a freshly scaffolded Python package (`src/ralf_spike_2/`) with no application code, no dependencies (FastAPI, SQLAlchemy, etc.), and only a placeholder test. Everything below must be built from scratch.

---

## Task 1: Project Setup & Dependencies
**Status:** Not started
**Spec:** N/A (infrastructure)

Add runtime and dev dependencies to `pyproject.toml`:
- Runtime: `fastapi`, `uvicorn[standard]`, `sqlalchemy`
- Dev: `httpx` (for TestClient)

Update `src/ralf_spike_2/__init__.py` with a meaningful docstring.

**Required tests:**
- (No tests — verified by successful `uv sync` and import)

---

## Task 2: Database Model & Engine Setup
**Status:** Not started
**Spec:** `specs/data-model.md`

Create `src/ralf_spike_2/database.py`:
- SQLAlchemy engine configured via `DATABASE_URL` env var (default: `sqlite:///data/todos.db`)
- `SessionLocal` factory
- `Base` declarative base
- `get_db` dependency for FastAPI

Create `src/ralf_spike_2/models.py`:
- `Todo` model: `id` (Integer, PK, autoincrement), `title` (String(500), not null), `completed` (Boolean, default False)
- Case-insensitive unique index on `title` (using `func.lower(title)`)

**Required tests:**
- Todo model has `id`, `title`, `completed` fields with correct types
- `id` is auto-generated
- `completed` defaults to `false`
- Case-insensitive unique constraint prevents duplicate titles (e.g., "Buy milk" and "buy milk")
- `title` max length is 500 characters

---

## Task 3: Pydantic Schemas
**Status:** Not started
**Spec:** `specs/data-model.md`, `specs/error-handling.md`

Create `src/ralf_spike_2/schemas.py`:
- `TodoCreate`: `title` (str, required). No `completed` field.
- `TodoUpdate` (PUT): `title` (str, required), `completed` (bool, optional, default False)
- `TodoPatch` (PATCH): `title` (str | None), `completed` (bool | None) — both optional
- `TodoResponse`: `id` (int), `title` (str), `completed` (bool)
- `PaginatedResponse`: `items` (list[TodoResponse]), `page` (int), `per_page` (int), `total` (int)
- `ErrorResponse`: `detail` (str)

**Required tests:**
- `TodoCreate` requires `title`, rejects missing title
- `TodoCreate` rejects non-string title
- `TodoUpdate` requires `title`, `completed` defaults to `false`
- `TodoPatch` allows both fields to be omitted but model validates at least one provided
- `TodoResponse` includes all three fields

---

## Task 4: FastAPI Application & Error Handling
**Status:** Not started
**Spec:** `specs/error-handling.md`

Create `src/ralf_spike_2/main.py`:
- FastAPI app instance
- Lifespan handler to create tables on startup
- Include todo router
- Custom exception handlers for consistent `{"detail": "..."}` format
- Override FastAPI's default 422 handler to return single `{"detail": "..."}` (not the default array format)

**Required tests:**
- All error responses use `{"detail": "..."}` format (not FastAPI's default validation error format)
- Only one error is returned per request
- Unknown fields in request bodies are silently ignored
- Type mismatches on recognised fields return 422 with descriptive message

---

## Task 5: Create Todo Endpoint
**Status:** Not started
**Spec:** `specs/create-todo.md`

Create `src/ralf_spike_2/routes.py` (or `router.py`) with `POST /todos`:
- Trim `title` whitespace before validation
- Validate: required, non-blank, max 500 chars, unique (case-insensitive)
- Return 201 with created todo object
- `completed` always `false` on creation (ignore if sent)

**Required tests:**
- Valid POST creates todo, returns 201 with `id`, `title`, `completed`
- Returned `id` is a unique auto-generated integer
- `completed` is always `false`
- Titles differing only by case → 409 duplicate
- Whitespace-only title → 422
- Title over 500 chars → 422
- Leading/trailing whitespace is trimmed in stored title
- Missing `title` → 422 with "title is required"
- Empty string `title` → 422 with "title must not be blank"
- `completed` in request body is silently ignored
- Non-string `title` (e.g., `123`) → 422

---

## Task 6: Retrieve Todos Endpoints
**Status:** Not started
**Spec:** `specs/retrieve-todos.md`

Implement `GET /todos` and `GET /todos/{id}`:
- List: return all todos ordered by `id` descending (newest first), as JSON array
- Single: return todo by `id`
- Validate `id` is a positive integer

**Required tests:**
- `GET /todos` returns 200 with all todos, newest first (descending `id`)
- `GET /todos` returns 200 with `[]` when no todos exist
- `GET /todos/{id}` returns 200 with matching todo
- `GET /todos/{id}` returns 404 when id doesn't exist
- `GET /todos/{id}` with non-integer id (e.g., "abc") returns 422
- `GET /todos/{id}` with negative or zero id returns 422
- Newest-first ordering verified with multiple todos

---

## Task 7: Update Todo Endpoints
**Status:** Not started
**Spec:** `specs/update-todo.md`

Implement four endpoints:
- `PUT /todos/{id}` — full replacement (`title` required, `completed` defaults to `false`)
- `PATCH /todos/{id}` — partial update (at least one field required)
- `POST /todos/{id}/complete` — set `completed = true`
- `POST /todos/{id}/incomplete` — set `completed = false`

All share validation: `id` valid+exists, title trimmed, non-blank, max 500, unique excluding self.

**Required tests:**
- PUT replaces `title` and `completed`; omitting `completed` resets to `false`
- PATCH updates only provided fields, leaves others unchanged
- PATCH with no recognised fields → 422 "at least one field must be provided"
- PATCH with only unknown fields → 422
- `POST .../complete` sets `completed = true`, returns todo
- `POST .../incomplete` sets `completed = false`, returns todo
- Both convenience endpoints are idempotent (calling twice succeeds)
- Update title to duplicate (case-insensitive, different todo) → 409
- Update title to whitespace-only → 422
- All update endpoints return 404 for non-existent id
- All update endpoints return 422 for non-integer id
- Title is trimmed on update
- PUT with missing `title` → 422
- PUT with title over 500 chars → 422

---

## Task 8: Delete Todo Endpoint
**Status:** Not started
**Spec:** `specs/delete-todo.md`

Implement `DELETE /todos/{id}`:
- Hard delete, return 204 No Content
- Validate `id` is positive integer, exists

**Required tests:**
- Deleting existing todo returns 204 with no body
- Todo is no longer retrievable after deletion (`GET` returns 404)
- Deleting non-existent id returns 404
- Deleting with non-integer id (e.g., "abc") returns 422
- Deleting with negative or zero id returns 422

---

## Task 9: Filtering, Sorting, Search & Pagination
**Status:** Not started
**Spec:** `specs/list-filtering-sorting-pagination.md`

Extend `GET /todos` with query parameters:
- `completed` filter (true/false)
- `search` (case-insensitive substring on title)
- `sort` (id or title), `order` (asc or desc)
- `page` and `per_page` pagination
- When any query param is present, return paginated envelope `{items, page, per_page, total}`
- When no query params, return plain array (backward compatible)

**Required tests:**
- `?completed=true` returns only completed todos
- `?completed=false` returns only incomplete todos
- `?search=buy` returns todos with "buy" in title (case-insensitive)
- Search + filter combined works
- `?sort=title&order=asc` sorts alphabetically ascending
- Default sort is `id` descending
- Paginated response includes `items`, `page`, `per_page`, `total`
- Page beyond total results returns empty `items` with correct `total`
- `per_page=1` returns one item per page
- Invalid `sort` value → 422
- Invalid `order` value → 422
- Invalid `completed` value → 422
- `page` < 1 or non-integer → 422
- `per_page` < 1, > 100, or non-integer → 422
- No query params → plain JSON array (backward compatible)
- Empty `search` string treated as no filter

---

## Task 10: Update README & Documentation
**Status:** Not started
**Spec:** N/A

Update `README.md` so a new developer can:
- Clone the repo
- Install dependencies (`uv sync --all-extras`)
- Run the app (`DATABASE_URL=sqlite:///data/todos.db uv run uvicorn ralf_spike_2.main:app`)
- Run tests (`uv run pytest`)
- Understand the API endpoints and project structure

Update `pyproject.toml` description field.

**Required tests:**
- (No code tests — manual/review verification)
