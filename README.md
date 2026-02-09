# ralf-spike-2

A Todo CRUD REST API built with FastAPI and SQLAlchemy, using async SQLite as the database backend.

## Running the App

```bash
# Install dependencies
uv sync --all-extras

# Start the server
uv run uvicorn ralf_spike_2.main:app

# Or with auto-reload for development
uv run uvicorn ralf_spike_2.main:app --reload
```

## Configuration

- `DATABASE_URL` — SQLAlchemy async database URL. Defaults to `sqlite+aiosqlite:///./todos.db`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /todos | Create a new todo |
| GET | /todos | List all todos (supports filtering, sorting, pagination) |
| GET | /todos/{id} | Get a single todo |
| PUT | /todos/{id} | Full replacement update |
| PATCH | /todos/{id} | Partial update |
| POST | /todos/{id}/complete | Mark as completed |
| POST | /todos/{id}/incomplete | Mark as incomplete |
| DELETE | /todos/{id} | Delete a todo |

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
