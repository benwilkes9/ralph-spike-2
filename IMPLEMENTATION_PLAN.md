# Implementation Plan

## Current State

The project is a freshly scaffolded Python package (`src/ralf_spike_2/`) with no application code, no dependencies (FastAPI, SQLAlchemy, etc.), and only a placeholder test. Everything below must be built from scratch.

All 7 spec files are in place under `specs/`:
- `data-model.md` — Todo schema, uniqueness, storage rules
- `create-todo.md` — POST /todos
- `retrieve-todos.md` — GET /todos, GET /todos/{id}
- `update-todo.md` — PUT, PATCH, POST complete/incomplete
- `delete-todo.md` — DELETE /todos/{id}
- `error-handling.md` — Consistent error format, validation order, unknown fields
- `list-filtering-sorting-pagination.md` — Query params on GET /todos

No new specs need to be authored.

---

## Task 1: Project Setup & Dependencies
**Status:** Not started
**Spec:** N/A (infrastructure)

Add runtime and dev dependencies to `pyproject.toml`:
- Runtime: `fastapi`, `uvicorn[standard]`, `sqlalchemy`
- Dev: `httpx` (for TestClient via `pytest`)

Update `src/ralf_spike_2/__init__.py` with a meaningful docstring (e.g., "A FastAPI-based Todo REST API.").

Run `uv sync --all-extras` to verify installation.

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
- `get_db` dependency (generator yielding session, for FastAPI `Depends`)

Create `src/ralf_spike_2/models.py`:
- `Todo` model: `id` (Integer, PK, autoincrement), `title` (String(500), not null), `completed` (Boolean, default False)
- Case-insensitive unique index on `title` (using `func.lower(title)`)

**Required tests:**
- Todo model has `id`, `title`, `completed` fields with correct types
- `id` is auto-generated when a row is inserted
- `completed` defaults to `false`
- Case-insensitive unique constraint prevents duplicate titles (e.g., "Buy milk" and "buy milk")
- `title` max length is 500 characters

---

## Task 3: Pydantic Schemas
**Status:** Not started
**Spec:** `specs/data-model.md`, `specs/error-handling.md`

Create `src/ralf_spike_2/schemas.py`:
- `TodoCreate`: `title` (str, required). No `completed` field. Configure `model_config = ConfigDict(extra="ignore")` so unknown fields are silently dropped.
- `TodoUpdate` (PUT): `title` (str, required), `completed` (bool, optional, default False). Also `extra="ignore"`.
- `TodoPatch` (PATCH): `title` (str | None = None), `completed` (bool | None = None) — both optional. `extra="ignore"`. Add a model validator to ensure at least one recognised field is provided.
- `TodoResponse`: `id` (int), `title` (str), `completed` (bool). Configure `from_attributes = True` for ORM mode.
- `PaginatedResponse`: `items` (list[TodoResponse]), `page` (int), `per_page` (int), `total` (int)
- `ErrorResponse`: `detail` (str)

**Required tests:**
- `TodoCreate` requires `title`, rejects missing title
- `TodoCreate` rejects non-string title (e.g., `123`)
- `TodoCreate` silently ignores unknown fields (e.g., `{"title": "x", "foo": "bar"}`)
- `TodoUpdate` requires `title`, `completed` defaults to `false`
- `TodoPatch` allows both fields to be omitted in schema but model validator rejects when neither is provided
- `TodoPatch` with only unknown fields (after `extra="ignore"`) fails validation
- `TodoResponse` includes all three fields and can be constructed from ORM model

---

## Task 4: FastAPI Application & Error Handling
**Status:** Not started
**Spec:** `specs/error-handling.md`

Create `src/ralf_spike_2/main.py`:
- FastAPI app instance
- Lifespan handler to create tables on startup (`Base.metadata.create_all`)
- Include todo router (from routes module)
- Custom exception handler for `RequestValidationError` to return single `{"detail": "..."}` string (not FastAPI's default array format)
- Custom exception handler for `HTTPException` to ensure consistent `{"detail": "..."}` format
- Handle path parameter validation (non-integer id → 422 with `"id must be a positive integer"`)

**Required tests:**
- All error responses use `{"detail": "..."}` format (string, not array)
- Only one error is returned per request
- Unknown fields in request bodies are silently ignored
- Type mismatches on recognised fields return 422 with descriptive message
- Path parameter validation errors (e.g., `GET /todos/abc`) return 422 with `{"detail": "id must be a positive integer"}`

---

## Task 5: Create Todo Endpoint
**Status:** Not started
**Spec:** `specs/create-todo.md`

Create `src/ralf_spike_2/routes.py` with `POST /todos`:
- Accept `TodoCreate` body (title only, unknown fields ignored)
- Trim `title` whitespace before validation
- Validate: non-blank after trim, max 500 chars, unique (case-insensitive)
- Return 201 with created todo object
- `completed` always `false` on creation (ignored if sent due to schema `extra="ignore"`)

**Required tests:**
- Valid POST creates todo, returns 201 with `id`, `title`, `completed`
- Returned `id` is a unique auto-generated integer
- `completed` is always `false`
- Titles differing only by case → 409 with `"A todo with this title already exists"`
- Whitespace-only title → 422 with `"title must not be blank"`
- Title over 500 chars → 422 with `"title must be 500 characters or fewer"`
- Leading/trailing whitespace is trimmed in stored title
- Missing `title` → 422 with `"title is required"`
- Empty string `title` → 422 with `"title must not be blank"`
- `completed` in request body is silently ignored
- Non-string `title` (e.g., `123`) → 422

---

## Task 6: Retrieve Todos Endpoints
**Status:** Not started
**Spec:** `specs/retrieve-todos.md`

Implement `GET /todos` and `GET /todos/{id}`:
- List: return all todos ordered by `id` descending (newest first), as JSON array
- Single: return todo by `id`
- Validate `id` is a positive integer (> 0); negative, zero, or non-integer → 422

**Required tests:**
- `GET /todos` returns 200 with all todos, newest first (descending `id`)
- `GET /todos` returns 200 with `[]` when no todos exist
- `GET /todos/{id}` returns 200 with matching todo
- `GET /todos/{id}` returns 404 with `"Todo not found"` when id doesn't exist
- `GET /todos/{id}` with non-integer id (e.g., "abc") returns 422
- `GET /todos/{id}` with negative or zero id returns 422
- Newest-first ordering verified with multiple todos

---

## Task 7: Update Todo Endpoints
**Status:** Not started
**Spec:** `specs/update-todo.md`

Implement four endpoints:
- `PUT /todos/{id}` — full replacement (`title` required, `completed` defaults to `false`)
- `PATCH /todos/{id}` — partial update (at least one recognised field required)
- `POST /todos/{id}/complete` — set `completed = true`
- `POST /todos/{id}/incomplete` — set `completed = false`

All share validation: `id` valid+exists, title trimmed, non-blank, max 500, unique excluding self.

**Required tests:**
- PUT replaces `title` and `completed`; omitting `completed` resets to `false`
- PATCH updates only provided fields, leaves others unchanged
- PATCH with no recognised fields → 422 `"at least one field must be provided"`
- PATCH with only unknown fields → 422 (unknown fields are ignored, so effectively empty)
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
- Hard delete, return 204 No Content (empty body)
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
- `completed` filter (`true`/`false`; other values → 422)
- `search` (case-insensitive substring on title; empty string = no filter)
- `sort` (`id` or `title`; other values → 422), `order` (`asc` or `desc`; other values → 422)
- `page` (positive integer, default 1) and `per_page` (integer 1–100, default 10)
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

Update `pyproject.toml` `description` field to something meaningful.

**Required tests:**
- (No code tests — manual/review verification)
