# ralf-spike-2

A Todo CRUD API built with FastAPI and SQLite (async via aiosqlite).

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Run the app
DATABASE_URL=sqlite:///data/todos.db uv run uvicorn ralf_spike_2.main:app

# Run tests
uv run pytest
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/todos` | Create a todo |
| `GET` | `/todos` | List all todos (supports filtering, search, sorting, pagination) |
| `GET` | `/todos/{id}` | Get a single todo |
| `PUT` | `/todos/{id}` | Full replacement update |
| `PATCH` | `/todos/{id}` | Partial update |
| `POST` | `/todos/{id}/complete` | Mark as complete |
| `POST` | `/todos/{id}/incomplete` | Mark as incomplete |
| `DELETE` | `/todos/{id}` | Delete a todo |

### Query Parameters (GET /todos)

When any query parameter is provided, the response uses a paginated envelope (`{items, page, per_page, total}`). Without query parameters, a plain JSON array is returned.

- `completed` — Filter by completion status (`true` or `false`)
- `search` — Case-insensitive substring match on title
- `sort` — Sort field: `id` (default) or `title`
- `order` — Sort direction: `asc` or `desc` (default)
- `page` — Page number, 1-indexed (default: 1)
- `per_page` — Items per page, 1–100 (default: 10)

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
