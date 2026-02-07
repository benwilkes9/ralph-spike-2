# Implementation Plan

## Current State

Freshly scaffolded Python package (`src/ralf_spike_2/`) with no application code, no runtime dependencies, and only a placeholder test. Everything below must be built from scratch. All tasks are "Not started."

Specs in `specs/`: `data-model.md`, `create-todo.md`, `retrieve-todos.md`, `update-todo.md`, `delete-todo.md`, `error-handling.md`, `list-filtering-sorting-pagination.md`.

## Dependency Graph

```
Task 1 (deps)
  -> Task 2 (database + model)
    -> Task 3 (schemas)
      -> Task 4 (app + error handling)
        -> Task 5 (POST /todos)
        -> Task 6 (GET /todos, GET /todos/{id})
        -> Task 7 (PUT, PATCH, POST complete/incomplete)
        -> Task 8 (DELETE /todos/{id})
        -> Task 9 (extends Task 6: filtering/sorting/pagination)
Task 10 (docs, after all others)
```

Tasks 5-8 depend on 1-4 but are independent of each other. Task 9 extends Task 6.

---

## Task 1: Project Setup & Dependencies
**Status:** Not started
**Spec:** N/A (infrastructure)
**Priority:** Foundation -- must be first

- Add runtime deps to `pyproject.toml` `dependencies`: `fastapi`, `uvicorn[standard]`, `sqlalchemy`
- Add `httpx` to `[project.optional-dependencies] dev` (required by FastAPI `TestClient`)
- Update `src/ralf_spike_2/__init__.py` docstring to `"A FastAPI-based Todo REST API."`
- Run `uv sync --all-extras` to verify

**Files to modify:**
- `pyproject.toml`
- `src/ralf_spike_2/__init__.py`

**Derived tests:**
- None (verified by successful `uv sync` and `import ralf_spike_2`)

---

## Task 2: Database Model & Engine Setup
**Status:** Not started
**Spec:** `specs/data-model.md`
**Priority:** Foundation -- depends on Task 1

Create `src/ralf_spike_2/database.py`:
- SQLAlchemy engine from `DATABASE_URL` env var (default: `sqlite:///data/todos.db`)
- `SessionLocal` session factory
- `Base` declarative base
- `get_db` dependency (generator yielding session, closes on exit)

Create `src/ralf_spike_2/models.py`:
- `Todo` model mapped to table `todos`
  - `id`: Integer, primary key, autoincrement
  - `title`: String(500), nullable=False
  - `completed`: Boolean, server_default=text("0") / default=False
- Case-insensitive unique index on `title` using `func.lower(title)`
- No timestamps, no soft-delete (per spec)

**Files to create:**
- `src/ralf_spike_2/database.py`
- `src/ralf_spike_2/models.py`

**Derived tests:**
- `Todo` model has `id`, `title`, `completed` columns with correct types
- Inserting a row auto-generates an integer `id`
- `completed` defaults to `false` when not specified
- Inserting two rows with titles differing only by case raises `IntegrityError`
- `title` column accepts a 500-character string
- `title` column rejects null (nullable=False)

---

## Task 3: Pydantic Schemas
**Status:** Not started
**Spec:** `specs/data-model.md`, `specs/error-handling.md`
**Priority:** Foundation -- depends on Task 2

Create `src/ralf_spike_2/schemas.py`:
- `TodoCreate`: `title: str` required. `model_config = ConfigDict(extra="ignore")`. No `completed` field.
- `TodoUpdate` (PUT): `title: str` required, `completed: bool = False`. `extra="ignore"`.
- `TodoPatch` (PATCH): `title: str | None = None`, `completed: bool | None = None`. `extra="ignore"`. Model validator: if both are `None` after parsing, reject.
- `TodoResponse`: `id: int`, `title: str`, `completed: bool`. `model_config = ConfigDict(from_attributes=True)`.
- `PaginatedResponse`: `items: list[TodoResponse]`, `page: int`, `per_page: int`, `total: int`.
- `ErrorResponse`: `detail: str`.

**Files to create:**
- `src/ralf_spike_2/schemas.py`

**Derived tests:**
- `TodoCreate` rejects missing `title` (raises `ValidationError`)
- `TodoCreate` silently drops unknown fields (e.g., `{"title": "x", "foo": "bar"}` parses without error)
- `TodoUpdate` requires `title`; `completed` defaults to `false` when omitted
- `TodoPatch` accepts `title` only, `completed` only, or both
- `TodoPatch` rejects when neither `title` nor `completed` is provided (model validator)
- `TodoPatch` with only unknown fields results in both `None` after stripping, triggering validator rejection
- `TodoResponse` can be constructed from an ORM model instance via `from_attributes`

---

## Task 4: FastAPI Application & Error Handling
**Status:** Not started
**Spec:** `specs/error-handling.md`
**Priority:** Foundation -- depends on Task 3

Create `src/ralf_spike_2/main.py`:
- FastAPI app instance (entry point: `ralf_spike_2.main:app`)
- Lifespan handler: `Base.metadata.create_all(bind=engine)` on startup
- Include router from `routes.py` (router created in Task 5, but import/include wired here)
- Custom `RequestValidationError` handler: return single `{"detail": "..."}` string (not FastAPI's default array)
- Custom `HTTPException` handler: ensure `{"detail": "..."}` format
- Validation order enforcement: missing field -> type error -> blank/whitespace -> length exceeded -> uniqueness violation
- Path parameter `{id}` validation: non-integer or non-positive -> 422 `"id must be a positive integer"`
- Only one error per response (never an array)

**Files to create:**
- `src/ralf_spike_2/main.py`

**Derived tests (from `specs/error-handling.md` acceptance criteria):**
- All error responses have shape `{"detail": "<string>"}` -- value is a string, never an array or object
- Only one error is returned per request, even when multiple validation failures exist
- Unknown fields in request bodies are silently ignored (no error for extra fields)
- `GET /todos/abc` returns 422 with `{"detail": "id must be a positive integer"}`
- `GET /todos/0` returns 422 with `{"detail": "id must be a positive integer"}`
- `GET /todos/-1` returns 422 with `{"detail": "id must be a positive integer"}`
- Missing required field returns 422 before type/format errors are checked
- Type mismatch on recognised field (e.g., `"title": 123`) returns 422

---

## Task 5: Create Todo Endpoint
**Status:** Not started
**Spec:** `specs/create-todo.md`
**Priority:** CRUD -- depends on Tasks 1-4

Create `src/ralf_spike_2/routes.py` with `APIRouter(prefix="/todos", tags=["todos"])`.

Implement `POST /todos`:
- Accept `TodoCreate` body (title only; unknown fields silently ignored via schema `extra="ignore"`)
- Trim `title` leading/trailing whitespace before any validation
- Validate in order: blank after trim -> length > 500 -> case-insensitive uniqueness
- `completed` always `false` on creation (schema does not accept it)
- Return 201 with created todo object

Wire router into `main.py` via `app.include_router(router)`.

**Files to create:**
- `src/ralf_spike_2/routes.py`

**Files to modify:**
- `src/ralf_spike_2/main.py` (include router)

**Derived tests (from `specs/create-todo.md` acceptance criteria):**
- Valid POST returns 201 with `{"id": <int>, "title": <str>, "completed": false}`
- Returned `id` is a unique auto-generated integer
- `completed` is always `false` on the returned object
- Missing `title` field -> 422 with `"title is required"`
- Empty string `""` title -> 422 with `"title must not be blank"`
- Whitespace-only title `"   "` -> 422 with `"title must not be blank"`
- Title over 500 characters -> 422 with `"title must be 500 characters or fewer"`
- Duplicate title (case-insensitive: "Buy milk" then "buy milk") -> 409 with `"A todo with this title already exists"`
- Leading/trailing whitespace is trimmed in the stored and returned title
- `completed` field in request body is silently ignored (todo still created with `completed: false`)
- Unknown fields (e.g., `"foo": "bar"`) are silently ignored
- Non-string `title` (e.g., `123`) -> 422 with type error message

---

## Task 6: Retrieve Todos Endpoints
**Status:** Not started
**Spec:** `specs/retrieve-todos.md`
**Priority:** CRUD -- depends on Tasks 1-4

Add to `src/ralf_spike_2/routes.py`:
- `GET /todos` -- return all todos ordered by `id` descending (newest first), as plain JSON array
- `GET /todos/{id}` -- return single todo by id

**Files to modify:**
- `src/ralf_spike_2/routes.py`

**Derived tests (from `specs/retrieve-todos.md` acceptance criteria):**
- `GET /todos` returns 200 with all todos, newest first (descending `id`)
- `GET /todos` returns 200 with `[]` when no todos exist
- `GET /todos/{id}` returns 200 with the matching todo object
- `GET /todos/{id}` with non-existent id -> 404 with `"Todo not found"`
- `GET /todos/{id}` with non-integer id (e.g., `"abc"`) -> 422 with `"id must be a positive integer"`
- `GET /todos/{id}` with `0` or negative id -> 422 with `"id must be a positive integer"`
- Newest-first ordering verified: create todo A then B, list returns B before A

---

## Task 7: Update Todo Endpoints
**Status:** Not started
**Spec:** `specs/update-todo.md`
**Priority:** CRUD -- depends on Tasks 1-4

Add to `src/ralf_spike_2/routes.py` four endpoints:
- `PUT /todos/{id}` -- full replacement (`title` required, `completed` defaults to `false`)
- `PATCH /todos/{id}` -- partial update (at least one recognised field required)
- `POST /todos/{id}/complete` -- set `completed = true`, no body, idempotent
- `POST /todos/{id}/incomplete` -- set `completed = false`, no body, idempotent

All share: id validation (positive integer, exists), title validation when provided (trim -> blank -> length -> uniqueness excluding self).

**Files to modify:**
- `src/ralf_spike_2/routes.py`

**Derived tests (from `specs/update-todo.md` acceptance criteria):**
- PUT replaces `title` and `completed`; omitting `completed` resets it to `false`
- PUT with missing `title` -> 422 with `"title is required"`
- PUT with blank title -> 422 with `"title must not be blank"`
- PUT with title > 500 chars -> 422 with `"title must be 500 characters or fewer"`
- PATCH updates only provided fields; omitted fields remain unchanged
- PATCH with `title` only updates title, leaves `completed` unchanged
- PATCH with `completed` only updates completed, leaves `title` unchanged
- PATCH with no recognised fields -> 422 with `"at least one field must be provided"`
- PATCH with only unknown fields -> 422 with `"at least one field must be provided"` (unknown fields stripped, effectively empty)
- `POST /todos/{id}/complete` sets `completed = true`, returns full todo with 200
- `POST /todos/{id}/incomplete` sets `completed = false`, returns full todo with 200
- Both convenience endpoints are idempotent (calling twice returns same result, no error)
- Update title to case-insensitive duplicate of a *different* todo -> 409 with `"A todo with this title already exists"`
- Update title to its own current value (same todo) -> succeeds (no self-conflict)
- Update title with leading/trailing whitespace -> stored trimmed
- Whitespace-only title on update -> 422 with `"title must not be blank"`
- All update endpoints with non-existent id -> 404 with `"Todo not found"`
- All update endpoints with non-integer id -> 422 with `"id must be a positive integer"`

---

## Task 8: Delete Todo Endpoint
**Status:** Not started
**Spec:** `specs/delete-todo.md`
**Priority:** CRUD -- depends on Tasks 1-4

Add to `src/ralf_spike_2/routes.py`:
- `DELETE /todos/{id}` -- hard delete, return 204 No Content (empty body)

**Files to modify:**
- `src/ralf_spike_2/routes.py`

**Derived tests (from `specs/delete-todo.md` acceptance criteria):**
- Deleting an existing todo returns 204 with no response body
- The deleted todo is no longer retrievable (`GET /todos/{id}` returns 404)
- The deleted todo no longer appears in `GET /todos` list
- Deleting a non-existent id -> 404 with `"Todo not found"`
- Deleting with non-integer id (e.g., `"abc"`) -> 422 with `"id must be a positive integer"`
- Deleting with `0` or negative id -> 422 with `"id must be a positive integer"`

---

## Task 9: Filtering, Sorting, Search & Pagination
**Status:** Not started
**Spec:** `specs/list-filtering-sorting-pagination.md`
**Priority:** Extension -- depends on Task 6

Extend `GET /todos` in `src/ralf_spike_2/routes.py` with optional query parameters:
- `completed`: `"true"` or `"false"` string; other values -> 422
- `search`: case-insensitive substring match on `title`; empty string = no filter
- `sort`: `"id"` (default) or `"title"`; other values -> 422
- `order`: `"asc"` or `"desc"` (default); other values -> 422
- `page`: positive integer >= 1, default 1; invalid -> 422
- `per_page`: integer 1-100, default 10; invalid -> 422

Response format branching:
- **Any query param present** -> paginated envelope: `{"items": [...], "page": int, "per_page": int, "total": int}`
- **No query params** -> plain JSON array (backward compatible with Task 6)

When `sort=title`, sorting is case-insensitive (use `func.lower(title)`).

**Files to modify:**
- `src/ralf_spike_2/routes.py`
- `src/ralf_spike_2/schemas.py` (if `PaginatedResponse` needs adjustment)

**Derived tests (from `specs/list-filtering-sorting-pagination.md` acceptance criteria):**
- `?completed=true` returns only completed todos
- `?completed=false` returns only incomplete todos
- `?completed=maybe` -> 422 with `"completed must be true or false"`
- `?search=buy` returns todos whose title contains "buy" (case-insensitive)
- Empty `?search=` treated as no filter (returns all)
- Search and filter combined: `?completed=true&search=buy` returns only completed todos containing "buy"
- `?sort=title&order=asc` returns todos sorted alphabetically ascending (case-insensitive)
- `?sort=title&order=desc` returns todos sorted alphabetically descending
- Default sort is `id` descending (newest first)
- `?sort=priority` -> 422 with `"sort must be 'id' or 'title'"`
- `?order=random` -> 422 with `"order must be 'asc' or 'desc'"`
- Paginated response includes `items`, `page`, `per_page`, `total` keys
- `?page=2&per_page=2` with 5 todos returns 2 items with `total: 5`
- Page beyond total results returns empty `items` with correct `total` (not an error)
- `?per_page=1` returns exactly one item per page
- `?page=0` -> 422 with `"page must be a positive integer"`
- `?page=-1` -> 422 with `"page must be a positive integer"`
- `?page=abc` -> 422 with `"page must be a positive integer"`
- `?per_page=0` -> 422 with `"per_page must be an integer between 1 and 100"`
- `?per_page=101` -> 422 with `"per_page must be an integer between 1 and 100"`
- `?per_page=abc` -> 422 with `"per_page must be an integer between 1 and 100"`
- No query params returns a plain JSON array (backward compatible with base retrieve)

---

## Task 10: Update README & Documentation
**Status:** Not started
**Spec:** N/A
**Priority:** Last -- after all functional tasks

- Update `README.md` with: clone, install (`uv sync --all-extras`), run app, run tests, type-check, lint, API endpoint summary, project structure
- Update `pyproject.toml` `description` to `"A FastAPI-based Todo REST API with SQLite backend."`

**Files to modify:**
- `README.md`
- `pyproject.toml`

**Derived tests:**
- None (manual/review verification)

---

## Summary: Exact Error Messages Reference

| Error Condition | Status | `detail` value |
|---|---|---|
| Missing `title` | 422 | `title is required` |
| Blank / whitespace-only `title` | 422 | `title must not be blank` |
| `title` > 500 chars | 422 | `title must be 500 characters or fewer` |
| Duplicate title (case-insensitive) | 409 | `A todo with this title already exists` |
| Invalid `id` (non-integer, zero, negative) | 422 | `id must be a positive integer` |
| Todo not found | 404 | `Todo not found` |
| PATCH with no recognised fields | 422 | `at least one field must be provided` |
| Invalid `completed` query param | 422 | `completed must be true or false` |
| Invalid `sort` query param | 422 | `sort must be 'id' or 'title'` |
| Invalid `order` query param | 422 | `order must be 'asc' or 'desc'` |
| Invalid `page` query param | 422 | `page must be a positive integer` |
| Invalid `per_page` query param | 422 | `per_page must be an integer between 1 and 100` |

## Validation Order (per `specs/error-handling.md`)

When multiple errors apply, return the **first** match in this order:
1. Missing required field
2. Type/format error
3. Blank / whitespace-only
4. Length exceeded
5. Uniqueness violation
