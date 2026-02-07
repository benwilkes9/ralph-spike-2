# ralf-spike-2

A Todo CRUD REST API built with FastAPI and SQLite. Provides full create, read, update, and delete operations for todo items with filtering, sorting, search, and pagination.

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Run the API server
uv run uvicorn ralf_spike_2.app:app

# Run the API server with auto-reload (development)
uv run uvicorn ralf_spike_2.app:app --reload
```

The server starts at `http://127.0.0.1:8000`. Interactive API docs are available at `http://127.0.0.1:8000/docs`.

## API Endpoints

### Create a Todo

```
POST /todos
```

Request body: `{"title": "Buy groceries"}` — returns 201 with the created todo.
`completed` is always `false` on creation.

### List Todos

```
GET /todos
```

Returns all todos as a JSON array (newest first). When query parameters are provided, returns a paginated envelope `{items, page, per_page, total}`.

**Query parameters:**

| Parameter   | Default | Description                                 |
|-------------|---------|---------------------------------------------|
| `completed` | —       | Filter: `true` or `false`                   |
| `search`    | —       | Case-insensitive substring match on title   |
| `sort`      | `id`    | Sort field: `id` or `title`                 |
| `order`     | `desc`  | Sort direction: `asc` or `desc`             |
| `page`      | `1`     | Page number (>= 1)                          |
| `per_page`  | `10`    | Items per page (1–100)                      |

### Get a Todo

```
GET /todos/{id}
```

### Update a Todo (full replacement)

```
PUT /todos/{id}
```

Request body: `{"title": "Updated title", "completed": true}` — `title` required, `completed` defaults to `false` if omitted.

### Update a Todo (partial)

```
PATCH /todos/{id}
```

Request body includes only the fields to update. At least one recognized field (`title` or `completed`) required.

### Mark Complete / Incomplete

```
POST /todos/{id}/complete
POST /todos/{id}/incomplete
```

No request body needed. Idempotent.

### Delete a Todo

```
DELETE /todos/{id}
```

Returns 204 with no body. Deletion is permanent.

## Error Handling

All errors return `{"detail": "Human-readable message"}`. Status codes: 404 (not found), 409 (duplicate title), 422 (validation failure).

## Development

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint and format
uv run ruff check src tests
uv run ruff format src tests

# Type check
uv run pyright

# Install pre-commit hooks
uv run pre-commit install
```
