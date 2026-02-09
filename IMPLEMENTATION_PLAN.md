# Implementation Plan: Todo CRUD REST API

All sections implemented and tested. 343 tests passing, pyright strict clean, ruff clean.

## Completed

All CRUD endpoints (1.x-6.x), error handling (5.x), filtering/sorting/pagination (4.x), structured logging (0.0.14), and test hardening (0.0.9-0.0.17) are complete. See git history for details.

## Boundary & Code-Path Test Hardening (0.0.18)

- **Audit-driven**: Deep code-path analysis identified 14 untested edge cases across LIKE wildcard escaping, logging internals, cross-field validation with null, path ID boundaries, and title reuse after deletion.
- **Search standalone wildcards (2)**: Search for `%` alone and `_` alone verifies LIKE escaping prevents matching everything. If escaping is wrong, `%` becomes `LIKE '%%'` matching all rows.
- **Logging formatter non-dict branch (1)**: Tests `_JsonFormatter` fallback path for non-dict log messages (`{"message": "..."}`). This code branch had zero coverage.
- **setup_logging() idempotency (1)**: Verifies multiple calls don't add duplicate handlers, preventing duplicate log lines per request.
- **Log query_string on 422 (1)**: Confirms query params are captured in log entries even when the request returns a validation error.
- **Path ID SQLite boundary (2)**: `2^63 - 1` (9223372036854775807) is accepted as valid ID (returns 404), while `2^63` (9223372036854775808) returns 422. Off-by-one boundary test.
- **PATCH cross-field null combos (2)**: `completed:null + title:""` returns completed type error (pri 2 before pri 3). `title:null + completed:null` returns title type error first.
- **PUT cross-field null combos (2)**: `completed:null + title>500` returns completed type error (pri 2 before pri 4). `title:true + completed:null` returns title type error.
- **PUT/PATCH reuse deleted title (2)**: Confirms hard-deleted titles are freed for reuse via PUT and PATCH, not just POST.
- **Paginated envelope field types (1)**: Asserts `total`, `page`, `per_page` are integers (type regression guard).
- **Total: 14 new tests**, bringing count from 329 to 343.

## Architecture Notes

- **PUT/PATCH field tracking**: Both handlers use raw body dict inspection rather than Pydantic model validators because `extra="ignore"` strips tracking fields. Route handlers check `"title" in body` and `"completed" in body` directly. This ensures consistent null handling (null != omitted).
- **Path param validation**: All `{todo_id}` params are typed as `str` to bypass FastAPI's built-in int conversion, enabling custom validation with consistent error messages.
- **Ruff config**: B008 suppressed for routes.py (FastAPI Depends pattern), TCH suppressed for test files (pytest fixture type hints need runtime imports).
- **SQLite AUTOINCREMENT**: Model uses `sqlite_autoincrement=True` in `__table_args__` to ensure deleted IDs are never reused per spec.
- **Cross-field validation**: PUT/PATCH validate type errors on all fields (title and completed) before blank/length on title. This matches the spec's priority ordering: missing(1) -> type(2) -> blank(3) -> length(4) -> uniqueness(5).
- **Search LIKE escaping**: The `\` character is used as the escape character in `ilike()` calls, with `%`, `_`, and `\` all properly escaped in search input.
- **JSON body validation**: `_parse_json_body` helper validates request body is a dict. `json.JSONDecodeError` handler in `main.py` catches malformed JSON. Both return 422 with `{"detail": "..."}`.
- **Path ID max value**: `_validate_path_id` rejects values > `2^63 - 1` to prevent SQLite OverflowError.
