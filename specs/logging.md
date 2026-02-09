# Cross-Cutting: Request Logging

## Purpose

Provide structured request/response logging for observability and debugging. Every HTTP request produces a single structured log entry after the response is sent.

## Log Format

Logs are emitted as JSON objects to stdout via Python's `logging` module at `INFO` level. Each log entry contains:

| Field          | Type    | Description                                            |
|----------------|---------|--------------------------------------------------------|
| `method`       | string  | HTTP method (e.g., `GET`, `POST`, `DELETE`)            |
| `path`         | string  | Request path (e.g., `/todos`, `/todos/1`)              |
| `query_string` | string  | Raw query string (empty string if none)                |
| `status_code`  | integer | HTTP response status code                              |
| `duration_ms`  | float   | Request processing time in milliseconds                |

## Log Levels

All request logs are emitted at `INFO` level. The application logger is named `todo_api`.

## Implementation Constraints

- Logging is implemented as ASGI middleware wrapping the FastAPI application.
- One log entry per request, emitted after the response is sent.
- `duration_ms` measures wall-clock time from request receipt to response completion.
- No sensitive data is logged (this API has no authentication, so all fields are safe).
- The JSON log format uses Python's standard `logging` module with a custom JSON formatter — no external dependencies required.

## Acceptance Criteria

1. Every HTTP request produces exactly one structured log entry at `INFO` level.
2. Log entry contains `method`, `path`, `query_string`, `status_code`, and `duration_ms`.
3. `duration_ms` is a non-negative float.
4. `status_code` matches the actual HTTP response status.
5. `method` and `path` match the request's HTTP method and URL path.
6. `query_string` is the raw query string (empty string when no query parameters).
7. Logger name is `todo_api`.
8. Log format is valid JSON.
9. Logging does not alter request/response behavior — all existing tests continue to pass unchanged.
