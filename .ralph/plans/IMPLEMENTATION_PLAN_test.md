# Implementation Plan — Todo REST API (`test` branch)

## Phase 1: Foundation

### Task 1.1: Project dependencies

- [ ] **Status:** Incomplete
- **Description:** Add all runtime and test dependencies to `pyproject.toml`. Runtime: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `aiosqlite`. Test/dev: `httpx`, `pytest-asyncio` (add to existing `dev` extras). Run `uv sync --all-extras` to verify resolution.
- **Spec(s):** `specs/test/data-model.md` (implies SQLAlchemy + SQLite)
- **Tests:**
  - `uv sync --all-extras` completes without errors.
  - `python -c "import fastapi, sqlalchemy, aiosqlite, uvicorn, httpx"` succeeds.

### Task 1.2: Database layer and ORM model

- [ ] **Status:** Incomplete
- **Description:** Create `src/ralf_spike_2/database.py` with async SQLAlchemy engine/session factory for SQLite (`aiosqlite`), supporting a `DATABASE_URL` env-var override (default `sqlite+aiosqlite:///./todos.db`). Create `src/ralf_spike_2/models.py` with a `TodoModel` ORM class: `id` (integer PK, autoincrement, never reused), `title` (string), `title_lower` (string, unique index for case-insensitive uniqueness), `completed` (boolean). Use `sqlite_autoincrement=True`. Provide an async `create_tables` helper.
- **Spec(s):** `specs/test/data-model.md`
- **Tests:**
  - The `todos` table is created with columns `id`, `title`, `title_lower`, `completed` (verified via `PRAGMA table_info`).
  - An in-memory database can insert and retrieve a row.
  - Inserting two rows with the same `title_lower` raises `IntegrityError` (unique index enforced).

### Task 1.3: Pydantic request/response schemas

- [ ] **Status:** Incomplete
- **Description:** Create `src/ralf_spike_2/schemas.py` with: `TodoCreate` (title required, `extra="ignore"`), `TodoUpdatePut` (title required, completed optional defaulting to `False`, `extra="ignore"`), `TodoUpdatePatch` (title optional, completed optional, validator requiring at least one field, `extra="ignore"`), `TodoResponse` (id, title, completed; `from_attributes=True`), `PaginatedResponse` (items, page, per_page, total).
- **Spec(s):** `specs/test/data-model.md`, `specs/test/create-todo.md`, `specs/test/update-todo.md`, `specs/test/list-filtering-sorting-pagination.md`
- **Tests:**
  - `TodoCreate(title="Buy milk")` sets title correctly.
  - `TodoCreate` without title raises `ValidationError`.
  - `TodoCreate` ignores unknown fields (e.g., `priority`).
  - `TodoUpdatePut` defaults `completed` to `False` when omitted.
  - `TodoUpdatePut` accepts explicit `completed=True`.
  - `TodoUpdatePatch` with no fields raises `ValidationError` ("At least one field must be provided").
  - `TodoUpdatePatch` accepts partial fields (title only, completed only).
  - `TodoResponse` serializes id, title, completed from ORM attributes.
  - `PaginatedResponse` includes items, page, per_page, total.

### Task 1.4: Application scaffold, error handling, and validation helpers

- [ ] **Status:** Incomplete
- **Description:** Create `src/ralf_spike_2/errors.py` with: `TodoNotFoundError` (404), `DuplicateTitleError` (409), `validate_path_id` (parses positive integer or raises 422), `validate_title` (trims, checks blank/length, raises 422), and a custom `RequestValidationError` handler that returns a single `{"detail": "..."}` message (not an array) following the validation priority order: missing → type/format → blank → length → uniqueness. Create `src/ralf_spike_2/app.py` (or `main.py`) with the FastAPI application, lifespan for DB setup, and the custom exception handler registered. Create `src/ralf_spike_2/routes.py` with an `APIRouter` stub (endpoints added in later tasks).
- **Spec(s):** `specs/test/error-handling.md`
- **Tests:**
  - The FastAPI app is importable without errors.
  - `GET /` returns 200 (health check / root endpoint).
  - All error responses use `{"detail": "..."}` format (not a list).
  - Only one error is returned per request.

---

## Phase 2: Core CRUD Endpoints

### Task 2.1: Create Todo — `POST /todos`

- [ ] **Status:** Incomplete
- **Description:** Implement `POST /todos` in `routes.py`. Accept `TodoCreate` body. Trim title, validate (blank, length), check case-insensitive uniqueness against DB, persist with `completed=False`, return 201 with the full todo object. `completed` in the request body is ignored (always `False` on creation).
- **Spec(s):** `specs/test/create-todo.md`
- **Tests:**
  - Valid POST returns 201 with `id`, `title`, `completed` fields.
  - Returned `id` is auto-generated; two successive creates yield different ids.
  - `completed` is always `false` on the returned object, even if sent in body.
  - Missing `title` returns 422 with detail `"title is required"`.
  - Empty string title returns 422 with detail `"title must not be blank"`.
  - Whitespace-only title (e.g., `"   "`) returns 422 with detail `"title must not be blank"`.
  - Title exceeding 500 characters returns 422 with detail `"title must be 500 characters or fewer"`.
  - Duplicate title differing only by case (e.g., `"Buy milk"` then `"buy milk"`) returns 409 with detail `"A todo with this title already exists"`.
  - Leading/trailing whitespace is trimmed in the stored and returned title.
  - Unknown fields in request body (e.g., `priority`) are silently ignored.

### Task 2.2: Retrieve Todos — `GET /todos` and `GET /todos/{id}`

- [ ] **Status:** Incomplete
- **Description:** Implement `GET /todos` returning all todos as a plain JSON array ordered by descending `id` (newest first). Implement `GET /todos/{id}` returning a single todo. Validate `id` is a positive integer.
- **Spec(s):** `specs/test/retrieve-todos.md`
- **Tests:**
  - `GET /todos` returns 200 with all todos ordered newest-first (descending id).
  - `GET /todos` returns 200 with `[]` when no todos exist.
  - `GET /todos/{id}` returns 200 with the matching todo object.
  - `GET /todos/{id}` for a non-existent id returns 404 with detail `"Todo not found"`.
  - `GET /todos/{id}` with a non-integer id (e.g., `"abc"`) returns 422 with detail `"id must be a positive integer"`.
  - `GET /todos/0` returns 422 (zero is not a positive integer).
  - `GET /todos/-1` returns 422 (negative is not a positive integer).

### Task 2.3: Update Todo — `PUT /todos/{id}`

- [ ] **Status:** Incomplete
- **Description:** Implement `PUT /todos/{id}` for full replacement. `title` is required; `completed` defaults to `False` if omitted (reset semantics). Trim title, validate, check uniqueness excluding the current todo, persist, return 200 with the updated object.
- **Spec(s):** `specs/test/update-todo.md`
- **Tests:**
  - PUT with title and completed replaces both fields, returns 200 with full todo.
  - PUT omitting `completed` resets it to `false`.
  - PUT missing `title` returns 422 with detail `"title is required"`.
  - PUT with blank title returns 422 with detail `"title must not be blank"`.
  - PUT with whitespace-only title returns 422.
  - PUT with title > 500 chars returns 422 with detail `"title must be 500 characters or fewer"`.
  - PUT with duplicate title (case-insensitive, different todo) returns 409.
  - PUT for non-existent id returns 404.
  - PUT with non-integer id returns 422.
  - PUT trims leading/trailing whitespace from title.
  - PUT ignores unknown fields in request body.
  - PUT where trimming creates a duplicate title returns 409.
  - PUT with a todo's own title (unchanged) succeeds (no false 409).

### Task 2.4: Update Todo — `PATCH /todos/{id}`

- [ ] **Status:** Incomplete
- **Description:** Implement `PATCH /todos/{id}` for partial update. Only provided fields are updated. At least one recognised field (`title` or `completed`) must be provided. Trim title if provided, validate, check uniqueness excluding current todo, return 200.
- **Spec(s):** `specs/test/update-todo.md`
- **Tests:**
  - PATCH updates only provided fields; omitted fields remain unchanged.
  - PATCH with title only leaves completed unchanged.
  - PATCH with completed only leaves title unchanged.
  - PATCH with no fields (empty body or `{}`) returns 422 with detail `"At least one field must be provided"`.
  - PATCH with only unknown fields returns 422 (unknown fields don't count).
  - PATCH with blank title returns 422.
  - PATCH with whitespace-only title returns 422.
  - PATCH with title > 500 chars returns 422.
  - PATCH with duplicate title (case-insensitive, different todo) returns 409.
  - PATCH for non-existent id returns 404.
  - PATCH with non-integer id returns 422.
  - PATCH trims title whitespace.
  - PATCH where trimming creates a duplicate returns 409.
  - PATCH with a todo's own title succeeds (no false 409).

### Task 2.5: Convenience endpoints — `POST /todos/{id}/complete` and `/incomplete`

- [ ] **Status:** Incomplete
- **Description:** Implement `POST /todos/{id}/complete` (sets `completed=True`) and `POST /todos/{id}/incomplete` (sets `completed=False`). Both are idempotent and return 200 with the full todo. Validate path id.
- **Spec(s):** `specs/test/update-todo.md`
- **Tests:**
  - `POST /todos/{id}/complete` sets `completed` to `true`, returns 200 with full todo.
  - Calling `/complete` on an already-complete todo succeeds (idempotent).
  - `POST /todos/{id}/incomplete` sets `completed` to `false`, returns 200 with full todo.
  - Calling `/incomplete` on an already-incomplete todo succeeds (idempotent).
  - `/complete` with non-existent id returns 404.
  - `/incomplete` with non-existent id returns 404.
  - `/complete` with non-integer id returns 422.
  - `/incomplete` with non-integer id returns 422.

### Task 2.6: Delete Todo — `DELETE /todos/{id}`

- [ ] **Status:** Incomplete
- **Description:** Implement `DELETE /todos/{id}`. Hard-deletes the todo and returns 204 with no body. Deleted ids are never reused (ensured by `sqlite_autoincrement`). Validate path id.
- **Spec(s):** `specs/test/delete-todo.md`
- **Tests:**
  - Deleting an existing todo returns 204 with empty body.
  - The deleted todo is no longer retrievable (GET returns 404).
  - Deleting a non-existent id returns 404.
  - Deleting with a non-integer id returns 422.
  - A new todo created after deletion has a higher id than the deleted one (ids never reused).

---

## Phase 3: Advanced Features

### Task 3.1: List filtering, sorting, search, and pagination — `GET /todos`

- [ ] **Status:** Incomplete
- **Description:** Extend `GET /todos` to support query parameters: `completed` (boolean filter), `search` (case-insensitive substring match on title), `sort` (`id` or `title`, default `id`), `order` (`asc` or `desc`, default `desc`), `page` (positive integer, default 1), `per_page` (1–100, default 10). When any query parameter is present, return a paginated envelope `{"items": [...], "page": N, "per_page": N, "total": N}`. When no query parameters are present, return a plain JSON array (backward compatible). Validate all parameters and return 422 for invalid values.
- **Spec(s):** `specs/test/list-filtering-sorting-pagination.md`
- **Tests:**
  - `?completed=true` returns only completed todos.
  - `?completed=false` returns only incomplete todos.
  - `?completed=invalid` returns 422 with detail `"completed must be true or false"`.
  - `?search=buy` returns todos with "buy" in title (case-insensitive).
  - Empty search string returns all todos.
  - `?completed=true&search=buy` combines filter and search.
  - `?sort=title&order=asc` sorts alphabetically ascending (case-insensitive).
  - `?sort=title&order=desc` sorts alphabetically descending.
  - `?sort=id&order=asc` sorts by id ascending.
  - Default sort (no params except one trigger) is id descending.
  - `?sort=invalid` returns 422 with detail `"sort must be 'id' or 'title'"`.
  - `?order=invalid` returns 422 with detail `"order must be 'asc' or 'desc'"`.
  - Response includes `items`, `page`, `per_page`, `total` when any param is provided.
  - Requesting a page beyond the last page returns empty `items` with correct `total`.
  - `?per_page=1` returns a single item per page.
  - `?page=0` returns 422 with detail `"page must be a positive integer"`.
  - `?page=-1` returns 422.
  - `?page=abc` returns 422.
  - `?per_page=0` returns 422 with detail `"per_page must be an integer between 1 and 100"`.
  - `?per_page=101` returns 422.
  - `?per_page=abc` returns 422.
  - `?per_page=100` is accepted (boundary).
  - Pagination offset/limit is correct for middle pages.
  - No query parameters returns a plain JSON array (backward compatible).

---

## Phase 4: Cross-Cutting Concerns

### Task 4.1: Error handling consistency

- [ ] **Status:** Incomplete
- **Description:** Verify and ensure all error responses across every endpoint use the `{"detail": "..."}` format (single string, not a list/array). Ensure validation priority order is enforced: missing field → type/format error → blank/whitespace → length exceeded → uniqueness violation. Only one error is returned per request. Unknown fields in request bodies are silently ignored. Type mismatches on recognised fields (e.g., `title: 123`, `completed: "yes"`) return 422.
- **Spec(s):** `specs/test/error-handling.md`
- **Tests:**
  - All error responses (404, 409, 422) use `{"detail": "..."}` format.
  - `detail` is always a string, never a list.
  - Validation errors return 422.
  - Uniqueness violations return 409.
  - Missing resources return 404.
  - Unknown fields in request bodies are silently ignored (no error).
  - PATCH with only unknown fields returns 422 ("At least one field must be provided").
  - `title` provided as integer (e.g., `{"title": 123}`) returns 422.
  - `completed` provided as string (e.g., `{"completed": "yes"}`) on PUT returns 422.
  - When title is missing, the error is `"title is required"` (missing takes priority over blank/length).

---

## Phase 5: Documentation

### Task 5.1: Developer documentation

- [ ] **Status:** Incomplete
- **Description:** Update `README.md` with: project description (Todo REST API), prerequisites (Python 3.12, `uv`), setup instructions (`uv sync --all-extras`), how to run the server (`uv run uvicorn ralf_spike_2.main:app`), how to run tests (`uv run pytest`), and a summary of available API endpoints. Ensure a new developer can clone the repo and get running.
- **Spec(s):** N/A (developer experience)
- **Tests:**
  - README contains setup, run, and test commands.
  - `uv run uvicorn ralf_spike_2.main:app` starts the server without errors.
