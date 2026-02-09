# Implementation Plan: Todo CRUD REST API

All sections implemented and tested. 373 tests passing, pyright strict clean, ruff clean.

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

## Spec-vs-Test Gap Analysis (0.0.19)

- **Audit-driven**: Deep spec-vs-test gap analysis compared every acceptance criterion and edge case in specs/ against all 343 existing tests. Identified 25 untested scenarios across validation ordering, 405 method restrictions, whitespace edge cases, and filter/sort/pagination boundaries.
- **Path ID before body validation (4)**: PUT/PATCH with invalid id + invalid body returns id error first. DELETE/complete with invalid id returns 422 regardless of body.
- **Additional 405 Method Not Allowed (4)**: PATCH/DELETE on `/complete`, PUT/PATCH on `/incomplete` all return 405.
- **Whitespace edge cases (4)**: Tab-only title, newline-only title, 600 spaces (blank not length error), 501 chars after trim (length error).
- **Incomplete endpoint ignores body (1)**: POST `/incomplete` with JSON body still succeeds.
- **PATCH completed true→false (1)**: Verifies toggling completed from true to false persists.
- **PUT/PATCH response id matches path (2)**: Response id equals path parameter id.
- **Delete does not affect other todos (1)**: Other todos remain unchanged after deletion.
- **Filter/sort case-sensitive (2)**: `order=DESC` and `sort=Title` both return 422.
- **Search + completed=false (1)**: Intersection of search and incomplete filter.
- **Search no match total zero (1)**: Empty search results have `total=0`.
- **Paginated without completed returns all (1)**: Omitting completed filter returns both completed and incomplete.
- **Very large page value (1)**: `page=999999999` returns empty items.
- **Search exact full title (1)**: Full title string search returns the todo.
- **Log entry for 405 (1)**: 405 responses produce log entries.
- **Total: 25 new tests**, bringing count from 343 to 368.

## Spec Gap Closure (0.0.20)

- **Audit-driven**: Opus deep analysis cross-referenced every spec line against all 368 tests. Found 5 genuine gaps.
- **POST /todos/{id} 405 (1)**: The single-item endpoint had no test for unsupported POST method.
- **405 response body format (1)**: All 10 existing 405 tests checked only status code, not that the body uses `{"detail": "..."}` format per error-handling spec.
- **Log entry field types (1)**: No explicit `isinstance` checks on `method` (str), `path` (str), `query_string` (str), `status_code` (int) per logging spec field type table.
- **Log entry exact key set (1)**: No test that log entries contain exactly the 5 spec-defined fields and no extras.
- **PUT completed:null only (1)**: PUT with only `completed:null` (no title) returns "title is required" (priority 1 missing before priority 2 type error).
- **Total: 5 new tests**, bringing count from 368 to 373.

## Architecture Notes

- **PUT/PATCH field tracking**: Both handlers use raw body dict inspection rather than Pydantic model validators because `extra="ignore"` strips tracking fields. Route handlers check `"title" in body` and `"completed" in body` directly. This ensures consistent null handling (null != omitted).
- **Path param validation**: All `{todo_id}` params are typed as `str` to bypass FastAPI's built-in int conversion, enabling custom validation with consistent error messages.
- **Ruff config**: B008 suppressed for routes.py (FastAPI Depends pattern), TCH suppressed for test files (pytest fixture type hints need runtime imports).
- **SQLite AUTOINCREMENT**: Model uses `sqlite_autoincrement=True` in `__table_args__` to ensure deleted IDs are never reused per spec.
- **Cross-field validation**: PUT/PATCH validate type errors on all fields (title and completed) before blank/length on title. This matches the spec's priority ordering: missing(1) -> type(2) -> blank(3) -> length(4) -> uniqueness(5).
- **Search LIKE escaping**: The `\` character is used as the escape character in `ilike()` calls, with `%`, `_`, and `\` all properly escaped in search input.
- **JSON body validation**: `_parse_json_body` helper validates request body is a dict. `json.JSONDecodeError` handler in `main.py` catches malformed JSON. Both return 422 with `{"detail": "..."}`.
- **Path ID max value**: `_validate_path_id` rejects values > `2^63 - 1` to prevent SQLite OverflowError.
