# Implementation Plan

All features implemented. 106 tests passing, pyright clean, ruff clean. Tagged `0.0.2`.

## Status

All spec acceptance criteria have corresponding tests. Full coverage across:
- CRUD endpoints (POST, GET, PUT, PATCH, DELETE)
- Convenience endpoints (complete/incomplete)
- Query params (filter, search, sort, order, page, per_page)
- Error handling (format, validation order, type mismatches, unknown fields)
- Edge cases (trim+uniqueness, self-exclusion, deleted ID reuse, non-integer params)

## Learnings

- FastAPI + `response_model=None` is required when returning `JSONResponse` directly (avoids Pydantic response model validation conflicts)
- `from __future__ import annotations` + FastAPI: imports used by FastAPI for request body parsing must stay at runtime (suppress `TC001`/`TC002` with `noqa`)
- Use `StrictBool` and `StrictStr` in Pydantic models to prevent type coercion (e.g., `"yes"` → `True`)
- FastAPI's `status_code=204` on `@router.delete` fails at import time — omit it and return `Response(status_code=204)` directly
- SQLite `COLLATE NOCASE` on unique index enforces case-insensitive uniqueness at the DB level
