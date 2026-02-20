# Implementation Plan — Todo REST API

## Overview

A production-ready REST API for managing Todo items, built with FastAPI and SQLite. The API supports full CRUD operations, filtering, sorting, search, and pagination.

---

## Task 1: [ ] Project Dependencies & App Scaffold

**Description:** Add FastAPI, Uvicorn, and SQLite/SQLAlchemy dependencies to `pyproject.toml`. Create the FastAPI application entry point with a health-check or root route. Configure the app to run with Uvicorn. Override FastAPI's default 422 validation error handler to return `{"detail": "..."}` (string) instead of the default Pydantic array format. Add a handler for malformed JSON request bodies returning 422 with `{"detail": "..."}`. This foundational error-handling setup is required before any endpoint tasks.

**Spec(s):** `specs/data-model.md`, `specs/error-handling.md`

**Tests:**
- The FastAPI app instance is importable from the package.
- `GET /` or a health endpoint returns a 200 response (optional, for smoke testing).
- The test client (`TestClient`) can be instantiated against the app without errors.
- FastAPI's default 422 response for Pydantic validation errors is overridden to use `{"detail": "..."}` (string, not array).
- Malformed JSON request body returns 422 with `{"detail": "..."}` format.

**Status:** `[ ]`

---

## Task 2: [ ] Database Layer & Todo Model

**Description:** Set up SQLAlchemy with SQLite. Define the `Todo` model with fields: `id` (auto-increment integer PK), `title` (string, max 500 chars, unique case-insensitive), `completed` (boolean, default `false`). Create a session/dependency for database access. Ensure `title` has a case-insensitive unique constraint. Implement table creation on app startup.

**Spec(s):** `specs/data-model.md`

**Tests:**
- A `Todo` record can be inserted and retrieved from the database.
- `id` is auto-generated as an incrementing integer.
- `completed` defaults to `false` when not specified.
- Inserting two todos with titles differing only by case raises a uniqueness violation at the DB level.
- `title` is stored as provided (trimming is an application concern, not DB).
- Deleted `id` values are never reused (SQLite auto-increment behavior).

**Status:** `[ ]`

---

## Task 3: [ ] Create Todo Endpoint (POST /todos)

**Description:** Implement `POST /todos` to create a new todo item. Accept `title` in the request body. Trim leading/trailing whitespace from `title` before validation. Validate: required, non-blank, max 500 chars, unique (case-insensitive). Ignore `completed` in request body (always default to `false`). Return 201 with the created todo object. Return appropriate error codes (422, 409) for validation failures.

**Spec(s):** `specs/create-todo.md`, `specs/error-handling.md`

**Tests:**
- Valid POST with `{"title": "Buy milk"}` returns 201 with `{"id": <int>, "title": "Buy milk", "completed": false}`.
- The returned `id` is a unique auto-generated integer.
- `completed` is always `false` on the returned object, even if `{"title": "X", "completed": true}` is sent.
- POST with missing `title` field returns 422 with `{"detail": "title is required"}`.
- POST with `{"title": ""}` returns 422 with `{"detail": "title must not be blank"}`.
- POST with `{"title": "   "}` (whitespace only) returns 422 with `{"detail": "title must not be blank"}`.
- POST with a title of 501 characters returns 422 with `{"detail": "title must be 500 characters or fewer"}`.
- POST with a title of exactly 500 characters returns 201 (boundary).
- Creating `"Buy milk"` then `"buy milk"` returns 409 with `{"detail": "A todo with this title already exists"}`.
- POST with `{"title": "  hello  "}` stores and returns `"hello"` (trimmed).
- POST with a title of 502 chars where 2 are leading/trailing spaces (trimmed = 500 chars) returns 201 (length validated after trimming).
- Creating `"  Buy milk  "` after `"Buy milk"` exists returns 409 (uniqueness checked on trimmed value).
- Unknown fields in the request body (e.g., `"foo": "bar"`) are silently ignored.
- POST with `{"title": 123}` (wrong type) returns 422.

**Status:** `[ ]`

---

## Task 4: [ ] Retrieve Todos Endpoints (GET /todos, GET /todos/{id})

**Description:** Implement `GET /todos` to return all todos as a JSON array, ordered by `id` descending (newest first). Implement `GET /todos/{id}` to return a single todo. Return 404 for non-existent id, 422 for non-integer id.

**Spec(s):** `specs/retrieve-todos.md`, `specs/error-handling.md`

**Tests:**
- `GET /todos` with no todos returns 200 with `[]`.
- `GET /todos` with 3 todos returns 200 with all 3, ordered by `id` descending.
- `GET /todos/1` returns 200 with the matching todo object.
- `GET /todos/999` (non-existent) returns 404 with `{"detail": "Todo not found"}`.
- `GET /todos/abc` (non-integer) returns 422 with `{"detail": "id must be a positive integer"}`.
- `GET /todos/0` returns 422 (not a positive integer).
- `GET /todos/-1` returns 422 (not a positive integer).

**Status:** `[ ]`

---

## Task 5: [ ] Update Todo — PUT /todos/{id}

**Description:** Implement `PUT /todos/{id}` for full replacement. `title` is required; `completed` is optional (defaults to `false` if omitted). Trim `title`, validate (non-blank, max 500, unique excluding self). Return 200 with updated todo.

**Spec(s):** `specs/update-todo.md`, `specs/error-handling.md`

**Tests:**
- PUT with `{"title": "New title"}` on existing todo returns 200 with `completed: false` (reset).
- PUT with `{"title": "New title", "completed": true}` returns 200 with `completed: true`.
- PUT omitting `completed` resets it to `false`.
- PUT with missing `title` returns 422 with `{"detail": "title is required"}`.
- PUT with blank title returns 422.
- PUT with `{"title": "   "}` (whitespace only) returns 422 with `{"detail": "title must not be blank"}`.
- PUT with title exceeding 500 chars returns 422.
- PUT with a title of exactly 500 characters returns 200 (boundary).
- PUT with duplicate title (case-insensitive, different todo) returns 409 with `{"detail": "A todo with this title already exists"}`.
- PUT updating a todo's title to its own current title (same id) succeeds (200).
- PUT on non-existent id returns 404.
- PUT on non-integer id returns 422.
- Title is trimmed before validation and storage.
- Unknown fields are silently ignored.

**Status:** `[ ]`

---

## Task 6: [ ] Update Todo — PATCH /todos/{id}

**Description:** Implement `PATCH /todos/{id}` for partial update. Only provided fields are updated; omitted fields remain unchanged. At least one recognized field must be provided. Same title validation rules apply when `title` is provided.

**Spec(s):** `specs/update-todo.md`, `specs/error-handling.md`

**Tests:**
- PATCH with `{"completed": true}` updates only `completed`, leaves `title` unchanged.
- PATCH with `{"title": "Updated"}` updates only `title`, leaves `completed` unchanged.
- PATCH with `{"title": "Updated", "completed": true}` updates both fields.
- PATCH with empty body `{}` returns 422 with `{"detail": "At least one field must be provided"}`.
- PATCH with only unknown fields `{"foo": "bar"}` returns 422 (treated as empty).
- PATCH with `{"title": "   "}` (whitespace only) returns 422 with `{"detail": "title must not be blank"}`.
- PATCH with title exceeding 500 chars returns 422.
- PATCH with duplicate title (case-insensitive, different todo) returns 409 with `{"detail": "A todo with this title already exists"}`.
- PATCH on non-existent id returns 404.
- PATCH on non-integer id returns 422.
- Title is trimmed when provided.
- PATCH with `{"completed": "yes"}` (wrong type) returns 422.

**Status:** `[ ]`

---

## Task 7: [ ] Convenience Endpoints — POST /todos/{id}/complete & /incomplete

**Description:** Implement `POST /todos/{id}/complete` to set `completed` to `true` and `POST /todos/{id}/incomplete` to set `completed` to `false`. Both are idempotent and return 200 with the full todo object. No request body required.

**Spec(s):** `specs/update-todo.md`, `specs/error-handling.md`

**Tests:**
- `POST /todos/1/complete` on an incomplete todo returns 200 with `completed: true`.
- `POST /todos/1/complete` on an already-complete todo returns 200 (idempotent, no change).
- `POST /todos/1/incomplete` on a complete todo returns 200 with `completed: false`.
- `POST /todos/1/incomplete` on an already-incomplete todo returns 200 (idempotent).
- Both endpoints return 404 for non-existent id.
- Both endpoints return 422 for non-integer id.

**Status:** `[ ]`

---

## Task 8: [ ] Delete Todo Endpoint (DELETE /todos/{id})

**Description:** Implement `DELETE /todos/{id}` to permanently remove a todo. Return 204 with no body on success. Return 404 for non-existent id, 422 for non-integer id.

**Spec(s):** `specs/delete-todo.md`, `specs/error-handling.md`

**Tests:**
- DELETE on existing todo returns 204 with empty body.
- The deleted todo is no longer retrievable via `GET /todos/{id}` (returns 404).
- DELETE on non-existent id returns 404 with `{"detail": "Todo not found"}`.
- DELETE on non-integer id (`/todos/abc`) returns 422 with `{"detail": "id must be a positive integer"}`.
- DELETE on `id=0` returns 422.
- DELETE on `id=-1` returns 422.

**Status:** `[ ]`

---

## Task 9: [ ] List Filtering, Sorting, Search & Pagination (GET /todos with query params)

**Description:** Extend `GET /todos` to support query parameters: `completed` (filter), `search` (case-insensitive substring), `sort` (`id` or `title`), `order` (`asc` or `desc`), `page` (1-indexed), `per_page` (1–100). When any query parameter is provided, return paginated envelope `{"items": [...], "page": N, "per_page": N, "total": N}`. When no query parameters are provided, return a plain JSON array (backward compatible).

**Spec(s):** `specs/list-filtering-sorting-pagination.md`, `specs/error-handling.md`

**Tests:**
- `GET /todos` with no params returns plain JSON array (backward compatible).
- `GET /todos?completed=true` returns only completed todos in paginated envelope.
- `GET /todos?completed=false` returns only incomplete todos in paginated envelope.
- `GET /todos?completed=maybe` returns 422 with `{"detail": "completed must be true or false"}`.
- `GET /todos?search=buy` returns todos whose title contains "buy" (case-insensitive).
- `GET /todos?search=` (empty string) returns all todos in paginated envelope (query param is present, but search filter is effectively ignored).
- `GET /todos?completed=true&search=buy` returns completed todos containing "buy".
- `GET /todos?sort=title&order=asc` returns todos sorted alphabetically ascending by title (case-insensitive).
- `GET /todos?sort=id&order=desc` returns todos sorted by id descending (default behavior).
- `GET /todos?sort=invalid` returns 422 with `{"detail": "sort must be 'id' or 'title'"}`.
- `GET /todos?order=invalid` returns 422 with `{"detail": "order must be 'asc' or 'desc'"}`.
- `GET /todos?page=1&per_page=2` with 5 todos returns 2 items, `total: 5`, `page: 1`.
- `GET /todos?page=100` (beyond last page) returns `{"items": [], "page": 100, ...}` with correct `total`.
- `GET /todos?page=0` returns 422 with `{"detail": "page must be a positive integer"}`.
- `GET /todos?page=abc` returns 422.
- `GET /todos?per_page=0` returns 422 with `{"detail": "per_page must be an integer between 1 and 100"}`.
- `GET /todos?per_page=101` returns 422.
- `GET /todos?per_page=1` returns one item per page.
- `GET /todos?per_page=abc` (non-integer) returns 422.
- `GET /todos?page=-1` returns 422.
- `GET /todos?completed=false` uses default sort `id` descending within paginated envelope.
- `GET /todos?completed=true` returns `total` reflecting only matching (completed) todos, not all todos.
- Default pagination when query params are present: `page=1`, `per_page=10`.

**Status:** `[ ]`

---

## Task 10: [ ] Error Handling & Validation Consistency

**Description:** Verify all error responses across all endpoints use the `{"detail": "..."}` format consistently. Verify validation order is enforced: missing field → type error → blank/whitespace → length exceeded → uniqueness violation. Only one error per request. (Note: the FastAPI default 422 override and malformed JSON handler are set up in Task 1; this task adds cross-cutting integration tests to verify consistency across all endpoints.)

**Spec(s):** `specs/error-handling.md`

**Tests:**
- All error responses across all endpoints use `{"detail": "..."}` format (not arrays, not nested).
- A request triggering multiple validation errors returns only the first per the priority order.
- Unknown fields in request bodies are silently ignored across all endpoints.
- A PATCH request with only unknown fields returns 422.
- Type mismatches on recognized fields (e.g., `"title": 123`, `"completed": "yes"`) return 422.

**Status:** `[ ]`

---

## Task 11: [ ] Documentation Update

**Description:** Update `README.md` so a new developer can clone the repo, follow instructions, and have the API running. Include: project description, prerequisites, install steps, how to run the dev server, how to run tests, API endpoint summary.

**Spec(s):** N/A (project-level documentation)

**Tests:**
- README includes project description.
- README includes install instructions (`uv sync --all-extras`).
- README includes how to start the server (e.g., `uv run uvicorn ...`).
- README includes how to run tests.
- README includes a brief API endpoint reference.

**Status:** `[ ]`
