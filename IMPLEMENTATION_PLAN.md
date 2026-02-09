# Implementation Plan: Todo CRUD API

## Technology Decisions

| Concern         | Choice                  | Rationale                                                                 |
|-----------------|-------------------------|---------------------------------------------------------------------------|
| Framework       | FastAPI                 | Spec error format `{"detail": "..."}` explicitly aligns with FastAPI      |
| ASGI server     | uvicorn                 | Standard production server for FastAPI                                    |
| Database        | SQLite (aiosqlite)      | Spec references SQLite auto-increment behaviour; async driver for FastAPI |
| ORM             | SQLAlchemy 2.x (async)  | Mature async SQLite support, model-level constraints, migration-friendly  |
| Test HTTP client| httpx                   | AsyncClient works natively with FastAPI's `TestClient` / ASGI transport   |
| Test framework  | pytest + pytest-asyncio | Already in dev deps (pytest); add pytest-asyncio + anyio for async tests  |
| Package root    | `src/ralf_spike_2/`     | Existing hatchling layout                                                 |

## Missing Spec Analysis

The seven spec files comprehensively cover the API's functional behaviour. The following elements are **not specified** but are relevant to a production deployment:

| Gap                        | Recommendation                                                                                      |
|----------------------------|-----------------------------------------------------------------------------------------------------|
| Technology stack           | Not a behavioural spec; captured in this plan's Technology Decisions table above. No spec needed.    |
| Health check endpoint      | Useful for container orchestration. Recommend adding `GET /health` returning `{"status": "ok"}` 200. No spec needed -- it is trivial and infrastructure-only. Implement it as part of the application scaffold task below. |
| API prefix / versioning    | Specs use bare `/todos`. No versioning prefix is implied. Do **not** add one unless explicitly requested. |
| CORS configuration         | Deployment concern, not API behaviour. Do not add unless explicitly requested.                       |
| Database file location     | Not specified. Use an environment variable `DATABASE_URL` defaulting to `sqlite+aiosqlite:///./todos.db`. Tests use an in-memory database. |

No new spec files need to be created. The existing specs are sufficient for implementation.

---

## Tasks

### Task 1 -- Dependencies and Project Configuration

- [x] **Add runtime and test dependencies to `pyproject.toml`**

**Description:** Add all runtime dependencies (`fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `aiosqlite`) to `[project] dependencies`. Add test dependencies (`httpx`, `pytest-asyncio`, `anyio`) to `[project.optional-dependencies] dev`. Ensure `uv sync --all-extras` installs everything.

**Spec(s):** N/A (infrastructure)

**Tests:**
- `uv sync --all-extras` completes without errors
- `uv run python -c "import fastapi; import uvicorn; import sqlalchemy; import aiosqlite; import httpx"` succeeds
- Existing `uv run pytest` still passes (package docstring test)

---

### Task 2 -- Database Layer

- [x] **Create SQLite connection management and Todo table schema**

**Description:** Create `src/ralf_spike_2/database.py` with:
- Async SQLAlchemy engine factory accepting a database URL (default from env var `DATABASE_URL`, falling back to `sqlite+aiosqlite:///./todos.db`)
- Async `sessionmaker` for dependency injection
- `create_tables()` coroutine for startup
- SQLAlchemy model `TodoModel` in `src/ralf_spike_2/models.py` with columns: `id` (Integer, primary key, autoincrement), `title` (String(500), not null), `title_lower` (String(500), unique index -- stores `title.lower()` for case-insensitive uniqueness), `completed` (Boolean, default False)

**Spec(s):** `specs/data-model.md`

**Tests:**
- Creating the tables on an in-memory SQLite database succeeds
- `TodoModel` has the correct column types and constraints
- Inserting a row with valid data succeeds and auto-generates an `id`
- Inserting two rows with `title_lower` collisions raises an IntegrityError
- `completed` defaults to `false` when not provided
- `title` longer than 500 characters can be stored at the DB level (validation is in the application layer) -- or alternatively, test that a CHECK constraint rejects it if we add one

---

### Task 3 -- Application Scaffold

- [x] **Create FastAPI application entry point with lifespan and health endpoint**

**Description:** Create `src/ralf_spike_2/app.py` with:
- FastAPI app instance with lifespan handler that calls `create_tables()` on startup
- Dependency `get_db` yielding async SQLAlchemy sessions
- `GET /health` returning `{"status": "ok"}` (200)
- Update `src/ralf_spike_2/__init__.py` to export the `app` object

**Spec(s):** N/A (infrastructure)

**Tests:**
- `GET /health` returns 200 with `{"status": "ok"}`
- App startup creates the `todos` table in the database
- Test client fixture is functional (can make requests to the app)

---

### Task 4 -- Pydantic Schemas (Request/Response Models)

- [x] **Define Pydantic models for all request and response shapes**

**Description:** Create `src/ralf_spike_2/schemas.py` with:
- `TodoCreate`: `title` (str, required). No `completed` field accepted.
- `TodoUpdatePut`: `title` (str, required), `completed` (bool, optional, default False). Use `strict=True` on `completed` so non-boolean types (e.g., integers, strings) are rejected as type errors rather than coerced.
- `TodoUpdatePatch`: `title` (str | None), `completed` (bool | None). Use `strict=True` on `completed`. Custom validator: at least one recognized field must be provided (i.e., not both `title is None and completed is None` after unknown fields are stripped).
- `TodoResponse`: `id` (int), `title` (str), `completed` (bool). Used for all single-todo responses.
- `PaginatedResponse`: `items` (list[TodoResponse]), `page` (int), `per_page` (int), `total` (int).
- All models must use `model_config = ConfigDict(extra="ignore")` so unknown fields are silently dropped.

**Spec(s):** `specs/data-model.md`, `specs/create-todo.md`, `specs/update-todo.md`, `specs/list-filtering-sorting-pagination.md`, `specs/error-handling.md`

**Tests:**
- `TodoCreate` rejects missing `title` (validation error)
- `TodoCreate` silently ignores `completed` and unknown fields
- `TodoUpdatePut` defaults `completed` to `false` when omitted
- `TodoUpdatePatch` raises validation error when no recognized fields are provided
- `TodoUpdatePatch` silently ignores unknown fields (and treats body with only unknown fields as empty)
- `TodoResponse` serialises all three fields correctly
- `PaginatedResponse` serialises envelope correctly

---

### Task 5 -- Error Handling Utilities

- [x] **Implement consistent error responses and validation helpers**

**Description:** Create `src/ralf_spike_2/errors.py` with:
- Override FastAPI's default `RequestValidationError` handler to return `{"detail": "..."}` with a single message following the validation order: missing -> type -> blank -> length -> uniqueness.
- Helper function `validate_path_id(id: str) -> int` that parses a path parameter as a positive integer or raises 422 with `"id must be a positive integer"`.
- Helper function `validate_title(title: str) -> str` that trims whitespace, checks blank, checks length (max 500), and returns the trimmed title or raises 422 with the appropriate message.
- Exception class or helper for 409 Conflict responses: `"A todo with this title already exists"`.
- Exception class or helper for 404 Not Found responses: `"Todo not found"`.

**Spec(s):** `specs/error-handling.md`, `specs/create-todo.md` (validation rules/order), `specs/update-todo.md` (validation rules/order)

**Tests:**
- Validation order is enforced: missing field takes priority over blank, blank over length, length over uniqueness
- `validate_path_id("abc")` raises 422 with correct message
- `validate_path_id("0")` raises 422 (not positive)
- `validate_path_id("-1")` raises 422
- `validate_path_id("3")` returns `3`
- `validate_title("  hello  ")` returns `"hello"`
- `validate_title("")` raises 422 with `"title must not be blank"`
- `validate_title("   ")` raises 422 with `"title must not be blank"`
- `validate_title("a" * 501)` raises 422 with `"title must be 500 characters or fewer"`
- All error responses use `{"detail": "..."}` format (single key, string value)
- Only one error returned per request (no arrays)

---

### Task 6 -- Create Todo Endpoint

- [x] **Implement `POST /todos`**

**Description:** Create `src/ralf_spike_2/routes/todos.py` (or a single `routes.py`) with an APIRouter. Implement `POST /todos`:
- Parse request body using `TodoCreate` schema (unknown fields ignored).
- If `title` key is missing entirely, return 422 `"title is required"`.
- If `title` is wrong type (e.g., integer), return 422 with type error message.
- Trim `title`, validate blank/length via `validate_title()`.
- Check case-insensitive uniqueness against database; return 409 if duplicate.
- Insert row with `completed=false`, return 201 with `TodoResponse`.
- `completed` field in request body must be silently ignored.

**Spec(s):** `specs/create-todo.md`, `specs/error-handling.md`

**Tests:**
- Valid POST with `{"title": "Buy milk"}` returns 201 with `{"id": 1, "title": "Buy milk", "completed": false}`
- Returned `id` is an auto-generated positive integer
- `completed` is always `false` regardless of whether `"completed": true` is sent
- POST with `{"title": "  Buy milk  "}` stores and returns `"Buy milk"` (trimmed)
- POST with `{"title": "Buy milk"}` then `{"title": "buy milk"}` returns 409
- POST with `{"title": "Buy milk"}` then `{"title": "Buy milk"}` returns 409
- POST with `{}` (missing title) returns 422 `"title is required"`
- POST with `{"title": ""}` returns 422 `"title must not be blank"`
- POST with `{"title": "   "}` returns 422 `"title must not be blank"`
- POST with `{"title": "a" * 501}` returns 422 `"title must be 500 characters or fewer"`
- POST with `{"title": "a" * 500}` succeeds (boundary)
- POST with `{"title": 123}` returns 422 (type error)
- POST with `{"title": "Buy milk", "foo": "bar"}` succeeds (unknown fields ignored)
- POST with `{"title": "Buy milk", "completed": true}` returns 201 with `completed: false`
- POST with `{"title": "Buy milk", "completed": "invalid"}` succeeds (completed is silently ignored, not type-validated since it's not accepted on create)
- POST with `{"foo": "bar"}` (only unknown fields, no title) returns 422 `"title is required"`
- POST with `{"title": ""}` when a duplicate exists returns 422 `"title must not be blank"` (blank takes priority over uniqueness per validation order)
- POST with title of 501 chars when a duplicate exists returns 422 `"title must be 500 characters or fewer"` (length takes priority over uniqueness)

---

### Task 7 -- Retrieve Todos Endpoints

- [x] **Implement `GET /todos` (list all) and `GET /todos/{id}` (get single)**

**Description:** Add to the todos router:
- `GET /todos`: Return all todos ordered by descending `id`. Returns a plain JSON array. Empty database returns `[]`.
- `GET /todos/{id}`: Validate `id` with `validate_path_id()`. Look up todo; return 404 if not found. Return 200 with `TodoResponse`.

**Spec(s):** `specs/retrieve-todos.md`

**Tests:**
- `GET /todos` with no todos returns 200 with `[]`
- `GET /todos` returns all todos ordered by descending `id` (newest first)
- Create 3 todos; `GET /todos` returns them in reverse creation order
- `GET /todos/1` returns 200 with the correct todo object
- `GET /todos/999` returns 404 `"Todo not found"`
- `GET /todos/abc` returns 422 `"id must be a positive integer"`
- `GET /todos/0` returns 422 `"id must be a positive integer"`
- `GET /todos/-1` returns 422 `"id must be a positive integer"`
- Response body for list is a plain JSON array (not an envelope)

---

### Task 8 -- Update Todo Endpoints

- [ ] **Implement `PUT /todos/{id}`, `PATCH /todos/{id}`, `POST /todos/{id}/complete`, `POST /todos/{id}/incomplete`**

**Description:** Add to the todos router:
- `PUT /todos/{id}`: Full replacement. `title` required. `completed` optional, defaults to `false` if omitted. Returns 200 with updated todo.
- `PATCH /todos/{id}`: Partial update. At least one recognized field required. Only provided fields are updated. Returns 200.
- `POST /todos/{id}/complete`: Sets `completed=true`. No request body. Idempotent. Returns 200.
- `POST /todos/{id}/incomplete`: Sets `completed=false`. No request body. Idempotent. Returns 200.
- All endpoints: validate path `id`, check existence (404), validate `title` if provided (trim, blank, length, uniqueness excluding self), return appropriate errors.

**Spec(s):** `specs/update-todo.md`, `specs/error-handling.md`

**Tests:**

*PUT /todos/{id}:*
- PUT with `{"title": "Updated"}` returns 200 with `completed: false` (reset to default)
- PUT with `{"title": "Updated", "completed": true}` returns 200 with `completed: true`
- PUT without `title` returns 422 `"title is required"`
- PUT with blank title returns 422
- PUT with title > 500 chars returns 422
- PUT with duplicate title (case-insensitive, different todo) returns 409
- PUT with same title as itself (case-insensitive) succeeds (e.g., updating "Buy Milk" to "buy milk" on the same todo succeeds)
- PUT to non-existent id returns 404
- PUT to non-integer id returns 422
- PUT with `{"title": "  Updated  "}` stores and returns `"Updated"` (trimmed)
- PUT with `{"title": "Valid", "completed": "yes"}` returns 422 (type error on completed)

*PATCH /todos/{id}:*
- PATCH with `{"title": "New"}` updates only title, `completed` unchanged
- PATCH with `{"completed": true}` updates only completed, `title` unchanged
- PATCH with `{"title": "New", "completed": true}` updates both
- PATCH with `{}` returns 422 `"At least one field must be provided"`
- PATCH with `{"foo": "bar"}` returns 422 (only unknown fields -- treated as empty)
- PATCH with duplicate title returns 409
- PATCH with same title as itself succeeds (e.g., updating "Buy Milk" to "buy milk" on the same todo succeeds)
- PATCH to non-existent id returns 404
- PATCH to non-integer id returns 422
- PATCH with `{"title": "  New  "}` stores and returns `"New"` (trimmed)
- PATCH with `{"completed": "yes"}` returns 422 (type error on completed)
- PATCH with `{"completed": 123}` returns 422 (type error on completed)

*POST /todos/{id}/complete:*
- Sets `completed` to `true`, returns 200 with full todo
- Calling on already-complete todo returns 200 (idempotent, no error)
- Non-existent id returns 404
- Non-integer id returns 422

*POST /todos/{id}/incomplete:*
- Sets `completed` to `false`, returns 200 with full todo
- Calling on already-incomplete todo returns 200 (idempotent, no error)
- Non-existent id returns 404
- Non-integer id returns 422

---

### Task 9 -- Delete Todo Endpoint

- [ ] **Implement `DELETE /todos/{id}`**

**Description:** Add to the todos router:
- Validate path `id` with `validate_path_id()`.
- Look up todo; return 404 if not found.
- Delete the row (hard delete).
- Return 204 with no body.

**Spec(s):** `specs/delete-todo.md`

**Tests:**
- Delete an existing todo returns 204 with empty body
- The deleted todo is no longer retrievable (`GET /todos/{id}` returns 404)
- The deleted todo does not appear in `GET /todos` list
- Delete non-existent id returns 404 `"Todo not found"`
- Delete non-integer id returns 422 `"id must be a positive integer"`
- Delete the same id twice: first returns 204, second returns 404
- Deleted `id` is never reused (create new todo after delete, its `id` is higher)

---

### Task 10 -- List Filtering, Sorting, Search, and Pagination

- [ ] **Extend `GET /todos` with query parameter support**

**Description:** Modify the `GET /todos` handler to detect query parameters and switch behaviour:
- **No query params:** Return plain JSON array (backward compatible, existing behaviour from Task 7).
- **Any query param present:** Apply filtering, sorting, pagination and return the envelope `{"items": [...], "page": N, "per_page": N, "total": N}`.
- **Filtering:** `completed=true|false` filters by completion status. Invalid values return 422.
- **Search:** `search=<string>` performs case-insensitive `LIKE '%string%'` on `title`. Empty string means no filter.
- **Sorting:** `sort=id|title` (default `id`), `order=asc|desc` (default `desc`). `sort=title` uses case-insensitive ordering. Invalid values return 422.
- **Pagination:** `page` (default 1, must be >= 1), `per_page` (default 10, range 1-100). Invalid values return 422. Page beyond results returns empty `items` with correct `total`.

**Spec(s):** `specs/list-filtering-sorting-pagination.md`

**Tests:**

*Filtering:*
- `?completed=true` returns only completed todos
- `?completed=false` returns only incomplete todos
- `?completed=invalid` returns 422 `"completed must be true or false"`

*Search:*
- `?search=buy` returns todos with "buy" in title (case-insensitive)
- `?search=BUY` also matches "Buy milk" (case-insensitive)
- `?search=` (empty) returns all todos (no filter applied)
- `?search=xyz` with no matches returns empty `items` list with `total: 0`

*Sorting:*
- `?sort=id&order=desc` returns newest first (default behaviour)
- `?sort=id&order=asc` returns oldest first
- `?sort=title&order=asc` returns alphabetical ascending (case-insensitive)
- `?sort=title&order=desc` returns reverse alphabetical (case-insensitive)
- `?sort=invalid` returns 422 `"sort must be 'id' or 'title'"`
- `?order=invalid` returns 422 `"order must be 'asc' or 'desc'"`

*Pagination:*
- `?page=1&per_page=2` with 5 todos returns 2 items, `total: 5`, `page: 1`, `per_page: 2`
- `?page=3&per_page=2` with 5 todos returns 1 item (last page)
- `?page=100&per_page=10` with 5 todos returns empty `items`, `total: 5`
- `?per_page=1` returns exactly 1 item per page
- `?per_page=100` works (max boundary)
- `?page=0` returns 422 `"page must be a positive integer"`
- `?page=-1` returns 422
- `?page=abc` returns 422
- `?per_page=0` returns 422 `"per_page must be an integer between 1 and 100"`
- `?per_page=101` returns 422
- `?per_page=abc` returns 422

*Combined:*
- `?completed=true&search=buy` returns only completed todos containing "buy"
- `?completed=false&sort=title&order=asc&page=1&per_page=5` combines all parameters
- Search + pagination: `total` reflects filtered count, not total database count

*Envelope vs. array:*
- No query params at all: response is a plain JSON array
- Any single query param present: response is an envelope object with `items`, `page`, `per_page`, `total`
- `?search=` (empty search, but param is present): response is an envelope

---

### Task 11 -- README and Documentation Updates

- [ ] **Update README.md with project description, setup, and run instructions**

**Description:** Update the existing `README.md` to include:
- Project description (Todo CRUD API built with FastAPI and SQLite)
- Python version requirement (>= 3.12)
- Setup instructions (`uv sync --all-extras`)
- How to run the application (`uv run uvicorn ralf_spike_2.app:app`)
- How to run tests (`uv run pytest`)
- Brief API endpoint reference (table of routes)
- Keep existing dev commands section

**Spec(s):** N/A (documentation)

**Tests:**
- N/A (manual review)
