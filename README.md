# Todo REST API

A production-ready REST API for managing Todo items, built with FastAPI and SQLite. Supports full CRUD operations, filtering, sorting, search, and pagination.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Getting Started

```bash
# Install dependencies
uv sync --all-extras

# Start the development server
uv run uvicorn ralf_spike_2.app:app --reload

# Run tests
uv run pytest tests/ -v

# Lint and type check
uv run ruff check src/ tests/
uv run pyright src/ tests/
```

## API Endpoints

All endpoints return errors in the format `{"detail": "message"}`.

### Health Check

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Returns `{"status": "ok"}` |

### Todos

| Method | Path | Description | Success |
|--------|------|-------------|---------|
| POST | `/todos` | Create a new todo | 201 |
| GET | `/todos` | List all todos (supports filtering, sorting, pagination) | 200 |
| GET | `/todos/{id}` | Get a single todo | 200 |
| PUT | `/todos/{id}` | Full update (replace) a todo | 200 |
| PATCH | `/todos/{id}` | Partial update a todo | 200 |
| DELETE | `/todos/{id}` | Delete a todo | 204 |
| POST | `/todos/{id}/complete` | Mark a todo as complete | 200 |
| POST | `/todos/{id}/incomplete` | Mark a todo as incomplete | 200 |

### Todo Object

```json
{
  "id": 1,
  "title": "Buy milk",
  "completed": false
}
```

### Creating a Todo

```bash
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
```

Title is trimmed, must be non-blank, at most 500 characters, and unique (case-insensitive). The `completed` field always defaults to `false`.

### Listing Todos

Without query parameters, `GET /todos` returns a plain JSON array ordered by `id` descending.

With any query parameter, it returns a paginated envelope:

```json
{
  "items": [{ "id": 1, "title": "Buy milk", "completed": false }],
  "page": 1,
  "per_page": 10,
  "total": 1
}
```

**Query Parameters:**

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `completed` | `true`, `false` | (none) | Filter by completion status |
| `search` | string | (none) | Case-insensitive substring match on title |
| `sort` | `id`, `title` | `id` | Sort field |
| `order` | `asc`, `desc` | `desc` | Sort direction |
| `page` | positive integer | `1` | Page number |
| `per_page` | 1-100 | `10` | Items per page |
