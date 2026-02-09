# ralf-spike-2

A Todo CRUD API built with FastAPI and SQLite.

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

```bash
uv sync --all-extras
```

## Running the Application

```bash
uv run uvicorn ralf_spike_2.app:app
```

The API will be available at `http://127.0.0.1:8000`. By default, data is stored in `./todos.db`. Set the `DATABASE_URL` environment variable to override (e.g. `DATABASE_URL=sqlite+aiosqlite:///./custom.db`).

## Running Tests

```bash
uv run pytest
```

Tests use an in-memory SQLite database and do not affect any on-disk data.

## API Endpoints

| Method   | Path                       | Description                                      |
|----------|----------------------------|--------------------------------------------------|
| `GET`    | `/health`                  | Health check — returns `{"status": "ok"}`         |
| `POST`   | `/todos`                   | Create a new todo                                |
| `GET`    | `/todos`                   | List all todos (supports filtering, sorting, search, pagination) |
| `GET`    | `/todos/{id}`              | Get a single todo by ID                          |
| `PUT`    | `/todos/{id}`              | Full replacement update of a todo                |
| `PATCH`  | `/todos/{id}`              | Partial update of a todo                         |
| `POST`   | `/todos/{id}/complete`     | Mark a todo as complete                          |
| `POST`   | `/todos/{id}/incomplete`   | Mark a todo as incomplete                        |
| `DELETE` | `/todos/{id}`              | Delete a todo                                    |

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
