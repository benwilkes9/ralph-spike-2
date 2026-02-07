# Implementation Plan

## Current State

The project is a freshly scaffolded Python package (`src/ralf_spike_2/`) with no application code, no runtime dependencies (FastAPI, SQLAlchemy, etc.), and only a placeholder test. Everything below must be built from scratch.

All 7 spec files are in place under `specs/`:
- `data-model.md` -- Todo schema, uniqueness, storage rules
- `create-todo.md` -- POST /todos
- `retrieve-todos.md` -- GET /todos, GET /todos/{id}
- `update-todo.md` -- PUT, PATCH, POST complete/incomplete
- `delete-todo.md` -- DELETE /todos/{id}
- `error-handling.md` -- Consistent error format, validation order, unknown fields
- `list-filtering-sorting-pagination.md` -- Query params on GET /todos

No new specs need to be authored.

---

## Task 1: Project Setup & Dependencies
**Status:** Not started
**Spec:** N/A (infrastructure)

Add runtime and dev dependencies to `pyproject.toml`:
- Runtime: `fastapi`, `uvicorn[standard]`, `sqlalchemy`
- Dev: `httpx` (required by FastAPI's `TestClient`)

Update `src/ralf_spike_2/__init__.py` docstring to `"A FastAPI-based Todo REST API."`.

Run `uv sync --all-extras` to verify installation.

**Files to create/modify:**
- Modify `pyproject.toml`
- Modify `src/ralf_spike_2/__init__.py`

**Required tests:**
- (No code tests -- verified by successful `uv sync` and import)

---

## Task 2: Database Model & Engine Setup
**Status:** Not started
**Spec:** `specs/data-model.md`

Create `src/ralf_spike_2/database.py`:
- SQLAlchemy engine configured via `DATABASE_URL` env var (default: `sqlite:///data/todos.db`)
- `SessionLocal` factory
- `Base` declarative base
- `get_db` dependency (generator yielding a session, for FastAPI `Depends`)

Create `src/ralf_spike_2/models.py`:
- `Todo` model: `id` (Integer, PK, autoincrement), `title` (String(500), not null), `completed` (Boolean, default False)
- Case-insensitive unique index on `title` (using `func.lower(title)`)
- No timestamps, no soft-delete flag (per spec)

**Files to create/modify:**
- Create `src/ralf_spike_2/database.py`
- Create `src/ralf_spike_2/models.py`

**Required tests:**
- Todo model has `id`, `title`, `completed` fields with correct types
- `id` is auto-generated when a row is inserted
- `completed` defaults to `false`
- Case-insensitive unique constraint prevents duplicate titles (e.g., "Buy milk" and "buy milk")
- `title` column accepts up to 500 characters

---

## Task 3: Pydantic Schemas
**Status:** Not started
**Spec:** `specs/data-model.md`, `specs/error-handling.md`

Create `src/ralf_spike_2/schemas.py`:
- `TodoCreate`: `title` (str, required). No `completed` field accepted. Configure `model_config = ConfigDict(extra="ignore")` so unknown fields are silently dropped.
- `TodoUpdate` (for PUT): `title` (str, required), `completed` (bool, optional, default False). Also `extra="ignore"`.
- `TodoPatch` (for PATCH): `title` (str | None = None), `completed` (bool | None = None) -- both optional. `extra="ignore"`. Add a model validator to ensure at least one recognised field is provided; a body with only unknown fields is treated as empty and must fail validation.
- `TodoResponse`: `id` (int), `title` (str), `completed` (bool). Configure `from_attributes = True` for ORM mode.
- `PaginatedResponse`: `items` (list[TodoResponse]), `page` (int), `per_page` (int), `total` (int).
- `ErrorResponse`: `detail` (str).

**Files to create/modify:**
- Create `src/ralf_spike_2/schemas.py`

**Required tests:**
- `TodoCreate` requires `title`; missing title raises validation error
- `TodoCreate` rejects non-string title (e.g., `123`)
- `TodoCreate` silently ignores unknown fields (e.g., `{"title": "x", "foo": "bar"}`)
- `TodoUpdate` requires `title`; `completed` defaults to `false` when omitted
- `TodoPatch` allows both fields to be individually optional but model validator rejects when neither recognised field is provided
- `TodoPatch` with only unknown fields (after `extra="ignore"` strips them) fails validation
- `TodoResponse` includes all three fields and can be constructed from an ORM model instance

---

## Task 4: FastAPI Application & Error Handling
**Status:** Not started
**Spec:** `specs/error-handling.md`

Create `src/ralf_spike_2/main.py`:
- FastAPI app instance (referenced as `ralf_spike_2.main:app` per AGENTS.md)
- Lifespan handler to create tables on startup (`Base.metadata.create_all`)
- Include todo router (from routes module, added in Task 5)
- Custom exception handler for `RequestValidationError` to return a single `{"detail": "..."}` string message (not FastAPI's default array format)
- Custom exception handler for `HTTPException` to ensure consistent `{"detail": "..."}` format
- Path parameter validation: non-integer or non-positive id returns 422 with `{"detail": "id must be a positive integer"}`
- Enforce validation order from spec: missing field -> type error -> blank/whitespace -> length exceeded -> uniqueness violation
- Only one error returned per response (no batch arrays)

**Files to create/modify:**
- Create `src/ralf_spike_2/main.py`

**Required tests:**
- All error responses use `{"detail": "..."}` format (value is a string, not an array)
- Only one error is returned per request, even when multiple validation failures apply
- Unknown fields in request bodies are silently ignored (no error for extra fields)
- Type mismatches on recognised fields return 422 with descriptive message
- Path parameter validation errors (e.g., `GET /todos/abc`) return 422 with `{"detail": "id must be a positive integer"}`
- Negative or zero path parameter id returns 422 with `{"detail": "id must be a positive integer"}`

---

## Task 5: Create Todo Endpoint
**Status:** Not started
**Spec:** `specs/create-todo.md`

Create `src/ralf_spike_2/routes.py` with an APIRouter. Implement `POST /todos`:
- Accept `TodoCreate` body (title only; unknown fields silently ignored via schema)
- Trim `title` whitespace before any validation or storage
- Validate in order: non-blank after trim, max 500 chars, case-insensitive uniqueness
- `completed` always set to `false` on creation (even if sent, schema ignores it)
- Return 201 with the created todo object

**Files to create/modify:**
- Create `src/ralf_spike_2/routes.py`
- Modify `src/ralf_spike_2/main.py` (include router)

**Required tests (from spec acceptance criteria):**
- Valid POST creates todo, returns 201 with `id`, `title`, `completed`
- Returned `id` is a unique auto-generated integer
- `completed` is always `false` on the returned object
- Titles differing only by case are rejected as duplicates: 409 with `"A todo with this title already exists"`
- Whitespace-only title returns 422 with `"title must not be blank"`
- Title over 500 chars returns 422 with `"title must be 500 characters or fewer"`
- Leading/trailing whitespace is trimmed in the stored title
- Missing `title` field returns 422 with `"title is required"`
- Empty string `title` returns 422 with `"title must not be blank"`
- `completed` sent in request body is silently ignored (todo still created with `completed=false`)
- Non-string `title` (e.g., `123`) returns 422

---

## Task 6: Retrieve Todos Endpoints
**Status:** Not started
**Spec:** `specs/retrieve-todos.md`

Add to `src/ralf_spike_2/routes.py`:
- `GET /todos` -- return all todos ordered by `id` descending (newest first), as a plain JSON array
- `GET /todos/{id}` -- return single todo by id
- Validate `id` is a positive integer; non-integer, negative, or zero returns 422 with `"id must be a positive integer"`

**Files to create/modify:**
- Modify `src/ralf_spike_2/routes.py`

**Required tests (from spec acceptance criteria):**
- `GET /todos` returns 200 with all todos, newest first (descending `id`)
- `GET /todos` returns 200 with `[]` when no todos exist
- `GET /todos/{id}` returns 200 with the matching todo
- `GET /todos/{id}` returns 404 with `"Todo not found"` for a non-existent id
- `GET /todos/{id}` with non-integer id (e.g., "abc") returns 422
- `GET /todos/{id}` with negative or zero id returns 422
- Newest-first ordering verified with multiple todos created in sequence

---

## Task 7: Update Todo Endpoints
**Status:** Not started
**Spec:** `specs/update-todo.md`

Add to `src/ralf_spike_2/routes.py` four endpoints:
- `PUT /todos/{id}` -- full replacement (`title` required, `completed` optional defaulting to `false`)
- `PATCH /todos/{id}` -- partial update (at least one recognised field required)
- `POST /todos/{id}/complete` -- set `completed = true` (no request body, idempotent)
- `POST /todos/{id}/incomplete` -- set `completed = false` (no request body, idempotent)

All share validation: `id` must be valid positive integer and refer to an existing todo. When `title` is provided, trim whitespace first, then validate: non-blank, max 500 chars, case-insensitive uniqueness excluding the current todo.

**Files to create/modify:**
- Modify `src/ralf_spike_2/routes.py`

**Required tests (from spec acceptance criteria):**
- PUT replaces `title` and `completed`; omitting `completed` resets it to `false`
- PATCH updates only the provided fields; omitted fields remain unchanged
- PATCH with no recognised fields returns 422 with `"at least one field must be provided"`
- PATCH with only unknown fields returns 422 (unknown fields are ignored, so effectively empty)
- `POST /todos/{id}/complete` sets `completed = true`, returns the full todo
- `POST /todos/{id}/incomplete` sets `completed = false`, returns the full todo
- Both convenience endpoints are idempotent (calling twice succeeds without error)
- Update title to a case-insensitive duplicate of a different todo returns 409 with `"A todo with this title already exists"`
- Update title to whitespace-only returns 422 with `"title must not be blank"`
- All update endpoints return 404 with `"Todo not found"` for a non-existent id
- All update endpoints return 422 for a non-integer id
- Title is trimmed of leading/trailing whitespace on update
- PUT with missing `title` returns 422 with `"title is required"`
- PUT with title over 500 chars returns 422 with `"title must be 500 characters or fewer"`

---

## Task 8: Delete Todo Endpoint
**Status:** Not started
**Spec:** `specs/delete-todo.md`

Add to `src/ralf_spike_2/routes.py`:
- `DELETE /todos/{id}` -- hard delete, return 204 No Content (empty body)
- Validate `id` is a positive integer and refers to an existing todo

**Files to create/modify:**
- Modify `src/ralf_spike_2/routes.py`

**Required tests (from spec acceptance criteria):**
- Deleting an existing todo returns 204 with no body
- The todo is no longer retrievable after deletion (`GET /todos/{id}` returns 404)
- Deleting a non-existent id returns 404 with `"Todo not found"`
- Deleting with a non-integer id (e.g., "abc") returns 422
- Deleting with a negative or zero id returns 422

---

## Task 9: Filtering, Sorting, Search & Pagination
**Status:** Not started
**Spec:** `specs/list-filtering-sorting-pagination.md`

Extend `GET /todos` in `src/ralf_spike_2/routes.py` with optional query parameters:
- `completed` filter: `true` or `false`; any other value returns 422 with `"completed must be true or false"`
- `search`: case-insensitive substring match on `title`; empty string treated as no filter
- `sort`: `id` (default) or `title`; other values return 422 with `"sort must be 'id' or 'title'"`
- `order`: `asc` or `desc` (default); other values return 422 with `"order must be 'asc' or 'desc'"`
- `page`: positive integer, default 1; invalid returns 422 with `"page must be a positive integer"`
- `per_page`: integer 1-100, default 10; invalid returns 422 with `"per_page must be an integer between 1 and 100"`

Response format:
- When **any** query parameter is present: return paginated envelope `{items, page, per_page, total}`
- When **no** query parameters are present: return plain JSON array (backward compatible with Task 6)

**Files to create/modify:**
- Modify `src/ralf_spike_2/routes.py`
- Possibly modify `src/ralf_spike_2/schemas.py` (if `PaginatedResponse` needs adjustments)

**Required tests (from spec acceptance criteria):**
- `?completed=true` returns only completed todos
- `?completed=false` returns only incomplete todos
- `?search=buy` returns todos whose title contains "buy" (case-insensitive)
- Search and filter can be combined (e.g., `?completed=true&search=buy`)
- `?sort=title&order=asc` returns todos sorted alphabetically ascending by title (case-insensitive)
- Default sort is `id` descending (newest first), matching base retrieve behaviour
- Paginated response includes `items`, `page`, `per_page`, `total`
- Page beyond total results returns empty `items` list with correct `total` (not an error)
- `per_page=1` returns exactly one item per page
- Invalid `sort` value returns 422 with `"sort must be 'id' or 'title'"`
- Invalid `order` value returns 422 with `"order must be 'asc' or 'desc'"`
- Invalid `completed` value returns 422 with `"completed must be true or false"`
- `page` < 1 or non-integer returns 422 with `"page must be a positive integer"`
- `per_page` < 1, > 100, or non-integer returns 422 with `"per_page must be an integer between 1 and 100"`
- No query params returns a plain JSON array (backward compatible)
- Empty `search` string is treated as no filter (returns all)

---

## Task 10: Update README & Documentation
**Status:** Not started
**Spec:** N/A

Update `README.md` so a new developer can:
- Clone the repo
- Install dependencies (`uv sync --all-extras`)
- Run the app (`DATABASE_URL=sqlite:///data/todos.db uv run uvicorn ralf_spike_2.main:app`)
- Run tests (`uv run pytest`)
- Run type checking (`uv run pyright`)
- Run linting (`uv run ruff check src tests`)
- Understand the API endpoints and project structure

Update `pyproject.toml` `description` field to `"A FastAPI-based Todo REST API with SQLite backend."`.

**Files to create/modify:**
- Modify `README.md`
- Modify `pyproject.toml`

**Required tests:**
- (No code tests -- manual/review verification)
