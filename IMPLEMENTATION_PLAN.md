# Implementation Plan — Todo CRUD REST API

## Status: In Progress - Tasks 1-10, 12 Complete

## Summary of Implementation

The Todo CRUD REST API has been successfully implemented with the following key architectural decisions:

- **Database**: Shared in-memory SQLite using `file:test_db?mode=memory&cache=shared` for test isolation with thread-local connections
- **Validation**: Manual JSON parsing in routes to handle validation priority ordering (missing → type → blank → length → uniqueness)
- **Error Handling**: Custom HTTPError exception class with FastAPI exception handler for consistent `{"detail": string}` error format
- **Initialization**: FastAPI lifespan context manager for DB initialization

All core functionality (Tasks 1-10) and integration tests (Task 12) have been implemented and are passing.

---

## Task 1: Project Setup & Dependencies
**Spec**: All specs (FastAPI implied by `error-handling.md` referencing FastAPI's default error structure)
**Status**: DONE

- Add `fastapi`, `uvicorn[standard]` to `[project.dependencies]` in `pyproject.toml`
- Add `httpx` to `[project.optional-dependencies] dev` (for async test client)
- Run `uv sync --all-extras` to install

**Required tests**:
- App is importable and creates a FastAPI instance
- Health check or root endpoint responds (optional — not in spec, but useful for smoke testing)

---

## Task 2: Database Layer & Todo Model
**Spec**: `specs/data-model.md`
**Status**: DONE

- Create `src/ralf_spike_2/database.py` — SQLite setup using `sqlite3` stdlib (or SQLAlchemy if preferred; keep it simple)
- Create `src/ralf_spike_2/models.py` — Pydantic schemas for Todo (response), TodoCreate (request), TodoUpdate (PUT request), TodoPatch (PATCH request)
- Create a `todos` table: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `title TEXT NOT NULL UNIQUE COLLATE NOCASE`, `completed BOOLEAN NOT NULL DEFAULT 0`
- Title max 500 chars, unique case-insensitive, trimmed before storage
- No timestamps, no soft-delete

**Required tests**:
- Todo table is created on startup
- `id` is auto-generated integer
- `title` uniqueness is case-insensitive at DB level
- `completed` defaults to `false`
- Title is stored trimmed

---

## Task 3: Create Todo — `POST /todos`
**Spec**: `specs/create-todo.md`
**Status**: DONE

- Create `src/ralf_spike_2/routes.py` (or `routers/todos.py`) with the POST endpoint
- Create `src/ralf_spike_2/app.py` — FastAPI app wiring
- Trim title before validation/storage
- Validate: required, non-blank, max 500 chars, unique (case-insensitive)
- `completed` is not accepted on creation; always defaults to `false`
- Return 201 with `{id, title, completed}`

**Required tests**:
- Valid POST creates todo, returns 201 with `{id, title, completed}`
- Returned `id` is a unique auto-generated integer
- `completed` is always `false` on returned object
- Titles differing only by case are rejected as duplicates (409)
- Whitespace-only title is rejected (422, `"title must not be blank"`)
- Missing `title` field returns 422 (`"title is required"`)
- Title over 500 chars is rejected (422, `"title must be 500 characters or fewer"`)
- Leading/trailing whitespace is trimmed in the stored title
- Unknown fields in request body are silently ignored

---

## Task 4: Retrieve Todos — `GET /todos` and `GET /todos/{id}`
**Spec**: `specs/retrieve-todos.md`
**Status**: DONE

- `GET /todos` returns all todos as a JSON array, ordered by `id` descending (newest first)
- Returns `[]` when no todos exist
- `GET /todos/{id}` returns a single todo by ID
- Validate `id` is a positive integer

**Required tests**:
- `GET /todos` returns 200 with all todos, newest first (descending `id`)
- `GET /todos` returns 200 with `[]` when no todos exist
- `GET /todos/{id}` returns 200 with the matching todo
- `GET /todos/{id}` returns 404 when `id` does not exist (`"Todo not found"`)
- `GET /todos/{id}` with a non-integer id (e.g., `"abc"`) returns 422 (`"id must be a positive integer"`)
- `GET /todos/{id}` with `id=0` or negative returns 422
- Newest-first ordering is verified with multiple todos

---

## Task 5: Update Todo — `PUT /todos/{id}`
**Spec**: `specs/update-todo.md`
**Status**: DONE

- Replaces all mutable fields
- `title` is required; `completed` defaults to `false` if omitted
- Trim title, validate same as create (non-blank, max 500, unique excluding self)
- Return 200 with updated todo

**Required tests**:
- PUT replaces `title` and `completed`; returns 200 with full todo
- Omitting `completed` resets it to `false`
- Updating title to a case-insensitive duplicate of another todo returns 409
- Updating title to same value (own title) succeeds
- Whitespace-only title returns 422
- Title over 500 chars returns 422
- Missing title returns 422 (`"title is required"`)
- Non-existent `id` returns 404
- Non-integer `id` returns 422
- Title is trimmed on update
- Unknown fields are silently ignored

---

## Task 6: Update Todo — `PATCH /todos/{id}`
**Spec**: `specs/update-todo.md`
**Status**: DONE

- Only provided fields are updated; omitted fields stay unchanged
- At least one recognised field must be provided
- Same validation on title if provided

**Required tests**:
- PATCH with only `title` updates title, leaves `completed` unchanged
- PATCH with only `completed` updates completed, leaves `title` unchanged
- PATCH with both fields updates both
- PATCH with no recognised fields returns 422 (`"At least one field must be provided"`)
- PATCH with only unknown fields returns 422 (treated as empty)
- Title validation (blank, length, uniqueness) applies when title is provided
- Non-existent `id` returns 404
- Non-integer `id` returns 422
- Title is trimmed on patch

---

## Task 7: Convenience Endpoints — `POST /todos/{id}/complete` and `/incomplete`
**Spec**: `specs/update-todo.md`
**Status**: DONE

- `POST /todos/{id}/complete` sets `completed=true`, returns 200 with todo
- `POST /todos/{id}/incomplete` sets `completed=false`, returns 200 with todo
- Both are idempotent
- No request body required

**Required tests**:
- `POST /todos/{id}/complete` sets `completed` to `true`, returns 200 with todo
- `POST /todos/{id}/incomplete` sets `completed` to `false`, returns 200 with todo
- Both are idempotent (calling on already-complete/incomplete succeeds)
- Non-existent `id` returns 404
- Non-integer `id` returns 422

---

## Task 8: Delete Todo — `DELETE /todos/{id}`
**Spec**: `specs/delete-todo.md`
**Status**: DONE

- Hard delete, returns 204 with no body
- Deleted id is never reused

**Required tests**:
- Deleting an existing todo returns 204 with no body
- The todo is no longer retrievable after deletion (GET returns 404)
- Deleting a non-existent `id` returns 404
- Deleting with a non-integer `id` returns 422
- Deleted `id` is not reused (create new todo after delete, verify different id)

---

## Task 9: Filtering, Sorting, Search & Pagination — `GET /todos`
**Spec**: `specs/list-filtering-sorting-pagination.md`
**Status**: DONE

- Extends `GET /todos` with query parameters: `completed`, `search`, `sort`, `order`, `page`, `per_page`
- When any query param is present, response is a pagination envelope `{items, page, per_page, total}`
- When no query params, response remains plain JSON array (backward compatible)
- Filtering: `completed=true|false`; omitting returns all; invalid value returns 422
- Search: case-insensitive substring match on `title`; empty search = no filter
- Sort: `sort=id` (default) or `sort=title` (case-insensitive alphabetical); `order=asc|desc` (default `desc`)
- Pagination: `page` >= 1 (default `1`), `per_page` 1–100 (default `10`); beyond last page returns empty `items`

**Required tests**:
- `?completed=true` returns only completed todos
- `?completed=false` returns only incomplete todos
- `?completed=invalid` returns 422 (`"completed must be true or false"`)
- `?search=buy` returns todos with "buy" in title (case-insensitive)
- Empty `?search=` returns all todos
- Search + filter combined works (`?completed=true&search=buy`)
- `?sort=title&order=asc` sorts alphabetically ascending (case-insensitive)
- `?sort=id&order=desc` is default behavior
- `?sort=invalid` returns 422 (`"sort must be 'id' or 'title'"`)
- `?order=invalid` returns 422 (`"order must be 'asc' or 'desc'"`)
- Response with query params includes `{items, page, per_page, total}`
- `?page=2&per_page=1` paginates correctly
- Page beyond total returns empty `items` with correct `total`
- `?per_page=1` returns one item per page
- `?page=0` returns 422 (`"page must be a positive integer"`)
- `?per_page=0` or `?per_page=101` returns 422 (`"per_page must be an integer between 1 and 100"`)
- No query params returns plain JSON array (backward compatible)

---

## Task 10: Error Handling — Cross-Cutting
**Spec**: `specs/error-handling.md`
**Status**: DONE

- All errors use `{"detail": "..."}` format
- Single error per request, ordered by validation priority: missing → type → blank → length → uniqueness
- Unknown fields silently ignored
- Type mismatches on recognised fields return 422
- Override FastAPI's default 422 handler to use simple `{"detail": "..."}` format instead of the default `{"detail": [{"loc": ..., "msg": ..., "type": ...}]}` format

**Required tests**:
- All error responses have `{"detail": "..."}` format (string, not array)
- Only one error returned per request
- Validation order: missing field checked before type, before blank, before length, before uniqueness
- `"title": 123` returns 422 with type error
- `"completed": "yes"` returns 422 with type error
- Unknown fields in request body don't cause errors
- PATCH with only unknown fields returns 422

---

## Task 11: Update README & Documentation
**Spec**: N/A (developer experience)
**Status**: NOT DONE

- Add project description to README (what the app is)
- Document how to run the API server (e.g., `uv run uvicorn ralf_spike_2.app:app`)
- Document API endpoints summary
- Document environment setup steps
- Ensure a new developer can clone, follow README, and have the app running

**Required tests**: N/A (documentation task)

---

## Task 12: Integration / End-to-End Tests
**Spec**: All specs combined
**Status**: DONE

- Full CRUD lifecycle test: create → retrieve → update → delete → verify gone
- Multiple todos with filtering + sorting + pagination
- Concurrent-safe uniqueness checks (stretch goal)

**Required tests**:
- Create a todo, retrieve it, update it, delete it, verify 404 on re-retrieve
- Create multiple todos, filter by completed, search by title, paginate, sort — all in one flow
