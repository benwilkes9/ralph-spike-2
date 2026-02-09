# Implementation Plan: Todo CRUD REST API

All sections implemented and tested. 304 tests passing, pyright strict clean, ruff clean.

## Completed

All CRUD endpoints (1.x–6.x), error handling (5.x), filtering/sorting/pagination (4.x), and test hardening (0.0.9–0.0.13) are complete. See git history for details.

## Structured Logging (0.0.14)

- **Spec**: `specs/logging.md` — structured JSON request/response logging via ASGI middleware.
- **Implementation**: `src/ralf_spike_2/logging_middleware.py` — `LoggingMiddleware` (ASGI) + `_JsonFormatter` + `setup_logging()`.
- **Integration**: Middleware added in `main.py` via `app.add_middleware(LoggingMiddleware)`. Logger configured during app lifespan startup.
- **Log fields**: `method`, `path`, `query_string`, `status_code`, `duration_ms` — emitted as JSON at INFO level via `todo_api` logger.
- **Tests (23)**: `tests/test_logging.py` — covers all 9 acceptance criteria: log entry per request, all fields present, non-negative duration, status code accuracy (200/201/204/404/409/422), method/path correctness for all HTTP methods, query string handling, logger name, JSON format validity, no alteration of existing behavior.
- **Why ASGI middleware**: Wraps the entire app including exception handlers, so even error responses are logged. `BaseHTTPMiddleware` would also work but raw ASGI is more lightweight.
- **pyright note**: `record.msg` is typed as `str` but we pass dicts at runtime; use `cast("dict[str, Any]", msg)` after `isinstance` check.
- **Total: 23 new tests**, bringing count from 238 to 261.

## Spec Compliance Test Hardening (0.0.15)

- **Audit-driven**: Deep spec compliance audit identified 26 test gaps across validation ordering, edge cases, and response shape.
- **Cross-field validation ordering**: Added tests for priority 2 (type error) before priority 4 (length) on both PUT and PATCH. Added tests for priority 1 (missing) before priority 2 on PUT with `title:null + completed:"yes"`. Added PATCH `title:null + completed:"yes"` (both type errors, title first). Added blank title with valid completed (priority 3 fires when priority 2 passes).
- **Case-insensitive self-exclusion**: Tests for PUT/PATCH updating a todo's title to a case-different version of its own title (e.g., "My Task" → "MY TASK") — must succeed via self-exclusion.
- **Trim-before-length on update**: Tests for PUT/PATCH where title exceeds 500 chars before trim but exactly 500 after trim — must be accepted. Previously only tested on POST.
- **Error response body shape**: Tests verifying 422/404/409 responses have ONLY the `detail` key (no extra keys leaking from FastAPI).
- **Missing ID validation**: Added zero/negative ID tests for PUT, PATCH, complete, delete endpoints (previously only some endpoints covered).
- **Unknown-fields-only**: Tests for POST/PUT with only unknown fields returning the correct validation error.
- **Length-before-uniqueness**: Tests for PUT/PATCH validation priority 4 before priority 5.
- **Misc edge cases**: PATCH `completed=false` on already-false todo (idempotent), POST with `completed: false` ignored, search with whitespace-only string.
- **Total: 26 new tests**, bringing count from 261 to 287.

## Test Quality Hardening (0.0.16)

- **Audit-driven**: Deep spec-vs-test audit identified assertion quality gaps and missing edge cases.
- **Fixed tautological assertion**: `test_create_id_field_ignored` had `assert x != 999 or x == 999` (always true); replaced with `isinstance(data["id"], int)`.
- **Exact error messages for malformed JSON**: Three tests (`test_create_invalid_json_body`, `test_put_invalid_json_body`, `test_patch_invalid_json_body`) upgraded from `"detail" in resp.json()` to exact string match `"Invalid JSON in request body"`.
- **Empty body tests (3)**: POST/PUT/PATCH with empty body (`content=b""`) — verifies JSONDecodeError handler fires for truly empty requests.
- **405 Method Not Allowed (4)**: GET/PUT on `/todos/{id}/complete`, GET/DELETE on `/todos/{id}/incomplete` — verifies only POST is allowed on convenience endpoints.
- **Response field type assertions (5)**: Explicit `isinstance` checks for `id: int`, `title: str`, `completed: bool` across GET, PUT, PATCH, complete, and list responses.
- **Trim + length + uniqueness combined (1)**: POST with 500-char title after trim that is a case-insensitive duplicate — tests all three constraints simultaneously.
- **Paginated completed is bool (1)**: Verifies `completed` in paginated list items is `bool`, not SQLite int 0/1.
- **Leading zeros/plus in page/per_page (3)**: Verifies `page=01`, `page=+1`, `per_page=010` are accepted (Python `int()` behavior).
- **Total: 17 new tests**, bringing count from 287 to 304.

## Architecture Notes

- **PUT/PATCH field tracking**: Both handlers use raw body dict inspection rather than Pydantic model validators because `extra="ignore"` strips tracking fields. Route handlers check `"title" in body` and `"completed" in body` directly. This ensures consistent null handling (null ≠ omitted).
- **Path param validation**: All `{todo_id}` params are typed as `str` to bypass FastAPI's built-in int conversion, enabling custom validation with consistent error messages.
- **Ruff config**: B008 suppressed for routes.py (FastAPI Depends pattern), TCH suppressed for test files (pytest fixture type hints need runtime imports).
- **SQLite AUTOINCREMENT**: Model uses `sqlite_autoincrement=True` in `__table_args__` to ensure deleted IDs are never reused per spec.
- **Cross-field validation**: PUT/PATCH validate type errors on all fields (title and completed) before blank/length on title. This matches the spec's priority ordering: missing(1) → type(2) → blank(3) → length(4) → uniqueness(5).
- **Search LIKE escaping**: The `\` character is used as the escape character in `ilike()` calls, with `%`, `_`, and `\` all properly escaped in search input.
- **JSON body validation**: `_parse_json_body` helper validates request body is a dict. `json.JSONDecodeError` handler in `main.py` catches malformed JSON. Both return 422 with `{"detail": "..."}`.
- **Path ID max value**: `_validate_path_id` rejects values > `2^63 - 1` to prevent SQLite OverflowError.
