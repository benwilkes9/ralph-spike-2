# Cross-Cutting: Error Handling

## Purpose

Define consistent error response structure across all endpoints.

## Error Response Format

All errors return a JSON object:

```json
{
  "detail": "Human-readable error message"
}
```

This aligns with FastAPI's default error response structure.

## HTTP Status Code Usage

| Code | Meaning              | Used When                                      |
|------|----------------------|------------------------------------------------|
| 200  | OK                   | Successful read or update                      |
| 201  | Created              | Successful resource creation                   |
| 204  | No Content           | Successful deletion                            |
| 404  | Not Found            | Resource id does not exist                     |
| 409  | Conflict             | Uniqueness constraint violated (duplicate title) |
| 422  | Unprocessable Entity | Validation failure (missing, blank, too long, invalid type) |

## Validation Order

When multiple validation errors apply, return the **first** matching error:

1. Missing required field
2. Type/format errors
3. Blank / whitespace-only
4. Length exceeded
5. Uniqueness violation

Only one error is returned per request (no batch error arrays).

## Unknown Fields

Request bodies may contain fields not defined by the API (e.g., `"foo": "bar"`). Unknown fields are **silently ignored**. Only recognised fields (`title`, `completed`) are processed. For PATCH requests, only recognised fields count toward the "at least one field must be provided" rule — a request body containing only unknown fields is treated as empty and returns 422.

## Type Validation

When a recognised field is provided with the wrong type (e.g., `"title": 123` or `"completed": "yes"`), the API returns **422** with a `{"detail": "..."}` message describing the type error. This applies to both request body fields and path parameters (e.g., `GET /todos/abc`).

## Acceptance Criteria

1. All error responses use the `{"detail": "..."}` format.
2. Only one error is returned per request.
3. Validation errors return 422.
4. Uniqueness violations return 409.
5. Missing resources return 404.
6. Unknown fields in request bodies are silently ignored.
7. A PATCH request with only unknown fields returns 422.
8. Type mismatches on recognised fields return 422.
