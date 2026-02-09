# Implementation Plan: Todo CRUD REST API

## 1. Project Setup (Dependencies & App Scaffold)

### 1.1 Add runtime dependencies to pyproject.toml
- **Description:** Add FastAPI, Uvicorn, SQLAlchemy[asyncio], aiosqlite, and Pydantic to the `dependencies` list in `pyproject.toml`. The API uses an async SQLite backend, so SQLAlchemy's async extensions and aiosqlite driver are required.
- **Spec(s):** All specs (foundational requirement)
- **Tests:**
  - [ ] Running `uv sync` succeeds without errors
  - [ ] FastAPI, SQLAlchemy, and Uvicorn are importable in the project virtualenv
- **Status:** [ ]

### 1.2 Add test dependencies (httpx, pytest-asyncio)
- **Description:** Add `httpx` (required by FastAPI's `TestClient` / async test client) and `pytest-asyncio` (for async test fixtures and tests) to the dev dependencies in `pyproject.toml`.
- **Spec(s):** All specs (test infrastructure)
- **Tests:**
  - [ ] `httpx` is importable in the test environment
  - [ ] A trivial TestClient request to a stub endpoint succeeds
- **Status:** [ ]

### 1.3 Create the FastAPI application entry point
- **Description:** Create `src/ralf_spike_2/main.py` with a FastAPI `app` instance. This is the object that Uvicorn will serve (`ralf_spike_2.main:app` as referenced in `AGENTS.md`). Include a lifespan context manager that creates database tables on startup. Register the todo router.
- **Spec(s):** All specs (foundational requirement), AGENTS.md operational notes
- **Tests:**
  - [ ] Importing `ralf_spike_2.main.app` returns a FastAPI application instance
  - [ ] The application starts without errors when given a test database URL
- **Status:** [ ]

## 2. Database Layer (Models, Connection, Migrations)

### 2.1 Create the SQLAlchemy model for Todo
- **Description:** Create `src/ralf_spike_2/models.py` defining a `Todo` SQLAlchemy model with columns: `id` (Integer, primary key, auto-increment), `title` (String(500), not nullable), `completed` (Boolean, default False). Add a case-insensitive unique index on `title` for enforcing uniqueness at the database level.
- **Spec(s):** data-model.md
- **Tests:**
  - [ ] The Todo model has `id`, `title`, and `completed` columns with correct types
  - [ ] The `id` column is auto-incrementing and serves as primary key
  - [ ] The `completed` column defaults to `false`
  - [ ] The `title` column enforces a maximum length of 500 characters
  - [ ] A case-insensitive unique constraint exists on `title`
- **Status:** [ ]

### 2.2 Create async database connection and session management
- **Description:** Create `src/ralf_spike_2/database.py` with async engine creation (using `create_async_engine` with aiosqlite driver), configurable via `DATABASE_URL` environment variable (defaulting to `sqlite+aiosqlite:///./todos.db`). Provide an async session factory (`async_sessionmaker`), and an async dependency function that yields an `AsyncSession` to route handlers. Include async table creation logic (using `async with engine.begin()` and `run_sync(Base.metadata.create_all)`) callable at app startup via FastAPI lifespan.
- **Spec(s):** data-model.md, AGENTS.md (DATABASE_URL=sqlite:///:memory: for tests, adapt to sqlite+aiosqlite:///:memory:)
- **Tests:**
  - [ ] The async engine connects successfully to an in-memory SQLite database
  - [ ] An async session dependency yields a usable session and closes it after use
  - [ ] Tables are created when the async initialization function is called
  - [ ] The `DATABASE_URL` environment variable is respected when set
- **Status:** [ ]

### 2.3 Create test fixtures for database and API client
- **Description:** Create a `tests/conftest.py` with pytest fixtures: an async in-memory SQLite engine (`sqlite+aiosqlite:///:memory:`), an async session override for dependency injection, a FastAPI `TestClient` (or `httpx.AsyncClient` with `httpx.ASGITransport`) wired to use the test database, and a helper fixture that creates sample todos for tests that need pre-existing data. Add `pytest-asyncio` to dev dependencies if async test fixtures are used.
- **Spec(s):** All specs (test infrastructure), AGENTS.md
- **Tests:**
  - [ ] The test client fixture is usable and makes requests to the app
  - [ ] Each test runs against a fresh, empty database (isolation)
  - [ ] The helper fixture creates todos that are retrievable via the API
- **Status:** [ ]

## 3. Core CRUD Endpoints

### 3.1 Create Todo — POST /todos
- **Description:** Implement the `POST /todos` endpoint in a router module (e.g., `src/ralf_spike_2/routes.py` or `src/ralf_spike_2/routers/todos.py`). Accept a JSON body with `title` (string, required). Trim leading/trailing whitespace from `title` before any validation. Validate in order: missing title, type/format errors, whitespace-only/blank, length > 500, case-insensitive uniqueness. The `completed` field is never accepted on create and always defaults to `false`. Return 201 with the full todo object on success. Return appropriate error responses (422, 409) on failure. Unknown fields in the request body are silently ignored.
- **Spec(s):** create-todo.md, error-handling.md, data-model.md
- **Tests:**
  - [ ] A valid POST with a title creates a todo and returns 201 with `id`, `title`, and `completed`
  - [ ] The returned `id` is a unique auto-generated integer
  - [ ] The returned `completed` is always `false`
  - [ ] Sending `completed: true` in the body is ignored; the created todo still has `completed: false`
  - [ ] Leading and trailing whitespace in `title` is trimmed in the response and storage
  - [ ] A request with missing `title` field returns 422 with detail "title is required"
  - [ ] A request with an empty string `title` returns 422 with detail about blank title
  - [ ] A request with a whitespace-only `title` returns 422 with detail about blank title
  - [ ] A request with `title` exceeding 500 characters returns 422 with detail about length
  - [ ] Creating a todo with the same title (case-insensitive) as an existing one returns 409
  - [ ] Titles "Buy milk" and "buy milk" are treated as duplicates
  - [ ] A title of exactly 500 characters is accepted
  - [ ] Unknown fields in the request body (e.g., `"foo": "bar"`) are silently ignored
  - [ ] Sending `title` as a non-string type (e.g., integer) returns 422
- **Status:** [ ]

### 3.2 Retrieve Todos — GET /todos and GET /todos/{id}
- **Description:** Implement `GET /todos` returning all todos as a JSON array, ordered by descending `id` (newest first). Returns 200 with an empty array when no todos exist. Implement `GET /todos/{id}` returning a single todo by id. Validate that `id` is a positive integer (return 422 if not). Return 404 if the todo does not exist.
- **Spec(s):** retrieve-todos.md, error-handling.md
- **Tests:**
  - [ ] `GET /todos` returns 200 with an empty array when no todos exist
  - [ ] `GET /todos` returns 200 with all todos ordered by descending `id` (newest first)
  - [ ] After creating multiple todos, the list order matches newest-first
  - [ ] `GET /todos/{id}` returns 200 with the matching todo object
  - [ ] `GET /todos/{id}` for a non-existent id returns 404 with detail "Todo not found"
  - [ ] `GET /todos/{id}` with a non-integer id (e.g., "abc") returns 422
  - [ ] `GET /todos/{id}` with zero returns 422 (not a positive integer)
  - [ ] `GET /todos/{id}` with a negative number returns 422
- **Status:** [ ]

### 3.3 Update Todo — PUT /todos/{id}
- **Description:** Implement `PUT /todos/{id}` for full replacement. `title` is required; `completed` is optional and defaults to `false` if omitted. All mutable fields are replaced. Title is trimmed before validation. Same validation rules as create apply (blank, length, case-insensitive uniqueness excluding self). Return 200 with the updated todo on success.
- **Spec(s):** update-todo.md, error-handling.md, data-model.md
- **Tests:**
  - [ ] PUT with valid `title` updates the todo and returns 200 with the updated object
  - [ ] PUT replaces both `title` and `completed` fields
  - [ ] PUT with `title` only resets `completed` to `false` (even if it was `true`)
  - [ ] PUT with `title` and `completed: true` sets both fields
  - [ ] PUT with missing `title` returns 422 with detail "title is required"
  - [ ] PUT with blank/whitespace-only `title` returns 422
  - [ ] PUT with `title` exceeding 500 characters returns 422
  - [ ] PUT with a duplicate title (case-insensitive, belonging to a different todo) returns 409
  - [ ] PUT updating a todo's title to its own current title (same id) succeeds (not a self-conflict)
  - [ ] PUT with a non-existent id returns 404
  - [ ] PUT with a non-integer id returns 422
  - [ ] Title whitespace is trimmed before storage on update
  - [ ] Unknown fields in the PUT body are silently ignored
- **Status:** [ ]

### 3.4 Update Todo — PATCH /todos/{id}
- **Description:** Implement `PATCH /todos/{id}` for partial update. Only provided fields are updated; omitted fields remain unchanged. At least one recognized field (`title` or `completed`) must be provided. Same title validation rules apply when title is provided. Unknown fields do not count toward the "at least one field" requirement. Return 200 with the updated todo on success.
- **Spec(s):** update-todo.md, error-handling.md
- **Tests:**
  - [ ] PATCH with only `title` updates the title and leaves `completed` unchanged
  - [ ] PATCH with only `completed` updates completed status and leaves `title` unchanged
  - [ ] PATCH with both `title` and `completed` updates both fields
  - [ ] PATCH with empty body `{}` returns 422 with detail "At least one field must be provided"
  - [ ] PATCH with only unknown fields (e.g., `{"foo": "bar"}`) returns 422
  - [ ] PATCH with blank/whitespace-only `title` returns 422
  - [ ] PATCH with `title` exceeding 500 characters returns 422
  - [ ] PATCH with a duplicate title (case-insensitive, different todo) returns 409
  - [ ] PATCH updating title to the same value (same todo) succeeds
  - [ ] PATCH with a non-existent id returns 404
  - [ ] PATCH with a non-integer id returns 422
  - [ ] Title whitespace is trimmed before storage on PATCH
  - [ ] Unknown fields alongside recognized fields are silently ignored
- **Status:** [ ]

### 3.5 Update Todo — POST /todos/{id}/complete and POST /todos/{id}/incomplete
- **Description:** Implement `POST /todos/{id}/complete` which sets `completed` to `true`, and `POST /todos/{id}/incomplete` which sets `completed` to `false`. Both are idempotent (calling complete on an already-complete todo is a no-op success). No request body is required. Return 200 with the full todo object.
- **Spec(s):** update-todo.md, error-handling.md
- **Tests:**
  - [ ] POST `/todos/{id}/complete` sets `completed` to `true` and returns 200 with the todo
  - [ ] POST `/todos/{id}/complete` on an already-completed todo succeeds with no change (idempotent)
  - [ ] POST `/todos/{id}/incomplete` sets `completed` to `false` and returns 200 with the todo
  - [ ] POST `/todos/{id}/incomplete` on an already-incomplete todo succeeds with no change (idempotent)
  - [ ] Both endpoints return 404 for a non-existent id
  - [ ] Both endpoints return 422 for a non-integer id
  - [ ] Both endpoints ignore any request body
- **Status:** [ ]

### 3.6 Delete Todo — DELETE /todos/{id}
- **Description:** Implement `DELETE /todos/{id}`. Permanently removes the todo (hard delete). Returns 204 No Content with an empty body on success. Validate that `id` is a positive integer (422 if not). Return 404 if the todo does not exist.
- **Spec(s):** delete-todo.md, error-handling.md
- **Tests:**
  - [ ] Deleting an existing todo returns 204 with no response body
  - [ ] The deleted todo is no longer retrievable via GET (returns 404)
  - [ ] The deleted todo's title can be reused for a new todo (uniqueness freed)
  - [ ] Deleting a non-existent id returns 404 with detail "Todo not found"
  - [ ] Deleting with a non-integer id (e.g., "abc") returns 422
  - [ ] Deleting with zero or negative id returns 422
- **Status:** [ ]

## 4. Advanced Features (Filtering, Sorting, Pagination)

### 4.1 Filtering by completion status
- **Description:** Extend `GET /todos` to accept a `completed` query parameter. `completed=true` returns only completed todos; `completed=false` returns only incomplete todos. Omitting the parameter returns all todos. Any value other than `true` or `false` returns 422.
- **Spec(s):** list-filtering-sorting-pagination.md, error-handling.md
- **Tests:**
  - [ ] `GET /todos?completed=true` returns only todos where `completed` is `true`
  - [ ] `GET /todos?completed=false` returns only todos where `completed` is `false`
  - [ ] `GET /todos?completed=yes` returns 422 with descriptive detail
  - [ ] `GET /todos?completed=1` returns 422
  - [ ] `GET /todos?completed=` returns 422
  - [ ] Filtering combined with other query params works correctly
- **Status:** [ ]

### 4.2 Search by title substring
- **Description:** Extend `GET /todos` to accept a `search` query parameter. Performs case-insensitive substring match on the `title` field. An empty `search` string is treated as no filter. Search combines with other filters.
- **Spec(s):** list-filtering-sorting-pagination.md
- **Tests:**
  - [ ] `GET /todos?search=buy` returns todos whose title contains "buy" (case-insensitive)
  - [ ] `GET /todos?search=BUY` also matches titles containing "buy"
  - [ ] `GET /todos?search=xyz` returns empty items when no title matches
  - [ ] `GET /todos?search=` (empty string) is treated as no filter and returns all todos
  - [ ] Search combined with `completed` filter returns the intersection of both filters
- **Status:** [ ]

### 4.3 Sorting
- **Description:** Extend `GET /todos` to accept `sort` and `order` query parameters. `sort` accepts `id` (default) or `title` (case-insensitive alphabetical). `order` accepts `asc` or `desc` (default). Invalid values return 422.
- **Spec(s):** list-filtering-sorting-pagination.md, error-handling.md
- **Tests:**
  - [ ] `GET /todos?sort=id&order=asc` returns todos sorted by ascending id
  - [ ] `GET /todos?sort=id&order=desc` returns todos sorted by descending id (default behavior)
  - [ ] `GET /todos?sort=title&order=asc` returns todos sorted alphabetically by title (case-insensitive)
  - [ ] `GET /todos?sort=title&order=desc` returns todos sorted reverse-alphabetically
  - [ ] Default sort (no params except one triggering envelope) is by `id` descending
  - [ ] `GET /todos?sort=invalid` returns 422
  - [ ] `GET /todos?order=invalid` returns 422
- **Status:** [ ]

### 4.4 Pagination
- **Description:** Extend `GET /todos` to accept `page` and `per_page` query parameters. `page` defaults to 1, `per_page` defaults to 10 (range 1-100). Results are paginated accordingly. `page` must be a positive integer; `per_page` must be between 1 and 100. Invalid values return 422.
- **Spec(s):** list-filtering-sorting-pagination.md, error-handling.md
- **Tests:**
  - [ ] `GET /todos?page=1&per_page=2` returns at most 2 items on the first page
  - [ ] `GET /todos?per_page=1` returns exactly 1 item per page
  - [ ] Requesting a page beyond the total number of pages returns empty `items` with correct `total`
  - [ ] `GET /todos?page=0` returns 422
  - [ ] `GET /todos?page=-1` returns 422
  - [ ] `GET /todos?page=abc` returns 422
  - [ ] `GET /todos?per_page=0` returns 422
  - [ ] `GET /todos?per_page=-1` returns 422
  - [ ] `GET /todos?per_page=101` returns 422
  - [ ] `GET /todos?per_page=abc` returns 422
- **Status:** [ ]

### 4.5 Response envelope logic (paginated vs. plain array)
- **Description:** When any query parameter is present on `GET /todos`, the response uses the pagination envelope format: `{"items": [...], "page": int, "per_page": int, "total": int}`. When no query parameters are provided, the response remains a plain JSON array for backward compatibility.
- **Spec(s):** list-filtering-sorting-pagination.md, retrieve-todos.md
- **Tests:**
  - [ ] `GET /todos` with no query params returns a plain JSON array (list of todo objects)
  - [ ] `GET /todos?page=1` returns the envelope format with `items`, `page`, `per_page`, and `total` keys
  - [ ] `GET /todos?completed=false` returns the envelope format
  - [ ] `GET /todos?search=` returns the envelope format (even though search is empty, a param is present)
  - [ ] `GET /todos?sort=title` returns the envelope format (sort param alone triggers envelope)
  - [ ] `GET /todos?order=asc` returns the envelope format (order param alone triggers envelope)
  - [ ] The `total` field reflects the count of matching items before pagination
  - [ ] The `page` and `per_page` fields in the response match the requested values (or defaults)
- **Status:** [ ]

## 5. Error Handling & Validation (Cross-Cutting)

### 5.1 Consistent error response format
- **Description:** Ensure all error responses across every endpoint use the `{"detail": "Human-readable message"}` JSON format. This includes 404, 409, and 422 responses. Override FastAPI's default validation error handler if necessary to match the single-string `detail` format rather than an array of validation errors.
- **Spec(s):** error-handling.md
- **Tests:**
  - [ ] Every 422 response body has a `detail` key with a string value (not an array)
  - [ ] Every 404 response body has a `detail` key with a string value
  - [ ] Every 409 response body has a `detail` key with a string value
  - [ ] No error response contains an `errors` array or nested validation structure
- **Status:** [ ]

### 5.2 Validation ordering
- **Description:** Ensure validation checks are applied in the specified priority order across all endpoints: (1) missing required field, (2) type/format errors, (3) blank/whitespace-only, (4) length exceeded, (5) uniqueness violation. Only the first matching error is returned per request.
- **Spec(s):** error-handling.md, create-todo.md, update-todo.md
- **Tests:**
  - [ ] A request with both missing title and other issues returns the "missing title" error first
  - [ ] A request with a non-string title returns a type error before blank/length checks
  - [ ] A request with a whitespace-only title returns blank error before length/uniqueness
  - [ ] A request with an over-length title returns length error before uniqueness check
  - [ ] Only one error is returned per request, never multiple
- **Status:** [ ]

### 5.3 Unknown field handling
- **Description:** Ensure unknown fields in request bodies are silently ignored across all endpoints. For PATCH, only recognized fields (`title`, `completed`) count toward the "at least one field" requirement. A PATCH body with only unknown fields returns 422.
- **Spec(s):** error-handling.md, update-todo.md
- **Tests:**
  - [ ] POST /todos with extra fields (e.g., `{"title": "Test", "priority": 1}`) creates the todo successfully, ignoring `priority`
  - [ ] PUT with extra fields updates normally, ignoring unknown fields
  - [ ] PATCH with `{"unknown_field": "value"}` only returns 422
  - [ ] PATCH with `{"title": "New", "unknown_field": "value"}` succeeds, ignoring the unknown field
- **Status:** [ ]

### 5.4 Type mismatch handling
- **Description:** Ensure that when recognized fields are provided with wrong types (e.g., `"title": 123`, `"completed": "yes"`), the API returns 422 with a descriptive detail message. This applies to request body fields and path parameters.
- **Spec(s):** error-handling.md
- **Tests:**
  - [ ] POST /todos with `{"title": 123}` returns 422 with a type-related detail message
  - [ ] POST /todos with `{"title": null}` returns 422
  - [ ] PUT with `{"title": "Valid", "completed": "yes"}` returns 422
  - [ ] PATCH with `{"completed": "yes"}` returns 422
  - [ ] `GET /todos/abc` returns 422 (path parameter type mismatch)
  - [ ] `DELETE /todos/abc` returns 422
- **Status:** [ ]

### 5.5 Path parameter validation for all endpoints
- **Description:** Ensure all endpoints that accept `{id}` in the path consistently validate that the id is a positive integer. Zero, negative numbers, non-numeric strings, and floats should all return 422 with detail "id must be a positive integer".
- **Spec(s):** error-handling.md, retrieve-todos.md, update-todo.md, delete-todo.md
- **Tests:**
  - [ ] `GET /todos/0` returns 422
  - [ ] `PUT /todos/-1` returns 422
  - [ ] `PATCH /todos/1.5` returns 422
  - [ ] `DELETE /todos/abc` returns 422
  - [ ] `POST /todos/abc/complete` returns 422
  - [ ] `POST /todos/0/incomplete` returns 422
  - [ ] All return detail "id must be a positive integer"
- **Status:** [ ]

## 6. Documentation & Project Configuration Updates

### 6.1 Update README.md
- **Description:** Update the README with a description of what the application does (a Todo CRUD REST API), how to run it (e.g., `uv run uvicorn ralf_spike_2.main:app`), the API endpoints overview, and a note about configuration (DATABASE_URL environment variable). Keep the existing development commands section.
- **Spec(s):** All specs (project documentation)
- **Tests:**
  - [ ] README contains a project description
  - [ ] README contains instructions for running the app
  - [ ] README contains a summary of available endpoints
- **Status:** [ ]

### 6.2 Update pyproject.toml project description
- **Description:** Update the empty `description` field in `pyproject.toml` to describe the project (e.g., "A Todo CRUD REST API built with FastAPI and SQLAlchemy").
- **Spec(s):** General project hygiene
- **Tests:**
  - [ ] The `description` field in `pyproject.toml` is non-empty and descriptive
- **Status:** [ ]

### 6.3 Update package docstring
- **Description:** Update the placeholder docstring in `src/ralf_spike_2/__init__.py` to accurately describe the package.
- **Spec(s):** General project hygiene
- **Tests:**
  - [ ] The existing `test_package_has_docstring` test continues to pass
  - [ ] The docstring is descriptive (not just a period)
- **Status:** [ ]
