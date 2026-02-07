# Implementation Plan

All tasks completed. 89 tests passing, pyright clean, ruff clean.

## Completed Tasks

- **Task 1**: Project dependencies — FastAPI, uvicorn, aiosqlite, httpx, pytest-asyncio
- **Task 2**: Database layer (`database.py`) and Pydantic models (`models.py`)
- **Task 3**: `POST /todos` with custom error handling (422 override, title validation, uniqueness)
- **Task 4**: `GET /todos` and `GET /todos/{id}`
- **Task 5**: `PUT /todos/{id}` — full replacement
- **Task 6**: `PATCH /todos/{id}` — partial update
- **Task 7**: `POST /todos/{id}/complete` and `/incomplete`
- **Task 8**: `DELETE /todos/{id}`
- **Task 9**: Query params — filtering (`completed`), search, sorting (`sort`/`order`), pagination (`page`/`per_page`), backward-compatible plain array when no params
- **Task 10**: Error handling consistency — `StrictBool`/`StrictStr` for type validation, single `{"detail": "..."}` format
- **Task 11**: README updated with project description, quick start, API endpoints, dev commands

## Learnings

- FastAPI + `response_model=None` is required when returning `JSONResponse` directly (avoids Pydantic response model validation conflicts)
- `from __future__ import annotations` + FastAPI: imports used by FastAPI for request body parsing must stay at runtime (suppress `TC001`/`TC002` with `noqa`)
- Use `StrictBool` and `StrictStr` in Pydantic models to prevent type coercion (e.g., `"yes"` → `True`)
- FastAPI's `status_code=204` on `@router.delete` fails at import time — omit it and return `Response(status_code=204)` directly
- SQLite `COLLATE NOCASE` on unique index enforces case-insensitive uniqueness at the DB level
