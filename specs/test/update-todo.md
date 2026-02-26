# JTBD 3: Update a Todo

## Job Statement

When I complete a task or need to change it, I need to update a todo.

## Endpoints

### Full Replacement

`PUT /todos/{id}`

#### Request Body

| Field   | Type   | Required | Notes                          |
|---------|--------|----------|--------------------------------|
| `title` | string | Yes      | Max 500 chars                  |

- `completed` is optional; defaults to `false` if omitted.

#### Behaviour

- Replaces all mutable fields on the todo.
- If `completed` is not provided, it resets to `false`.

### Partial Update

`PATCH /todos/{id}`

#### Request Body

| Field       | Type    | Required | Notes         |
|-------------|---------|----------|---------------|
| `title`     | string  | No       | Max 500 chars |
| `completed` | boolean | No       |               |

#### Behaviour

- Only provided fields are updated; omitted fields remain unchanged.
- At least one field must be provided.

### Mark Complete

`POST /todos/{id}/complete`

#### Behaviour

- Sets `completed` to `true`.
- No request body required.
- Idempotent: calling on an already-complete todo succeeds with no change.

### Mark Incomplete

`POST /todos/{id}/incomplete`

#### Behaviour

- Sets `completed` to `false`.
- No request body required.
- Idempotent: calling on an already-incomplete todo succeeds with no change.

## Validation Rules (all update endpoints)

1. `id` must be a valid positive integer and must refer to an existing todo.
2. When `title` is provided, leading/trailing whitespace is trimmed first. All subsequent checks (blank, length, uniqueness) apply to the **trimmed** value.
3. When `title` is provided, it must be non-empty, not whitespace-only, and max 500 characters.
4. When `title` is provided, it must remain unique (case-insensitive) — excluding the current todo from the uniqueness check.

## Response (all update endpoints)

- **200 OK** — returns the full updated todo object (`id`, `title`, `completed`).

## Error Scenarios

| Condition                      | Status | Detail                                      |
|--------------------------------|--------|---------------------------------------------|
| `id` not valid                 | 422    | `id` must be a positive integer             |
| `id` not found                 | 404    | Todo not found                              |
| Missing `title` on PUT         | 422    | `title` is required                         |
| Empty / whitespace `title`     | 422    | `title` must not be blank                   |
| `title` exceeds 500 chars      | 422    | `title` must be 500 characters or fewer     |
| Duplicate title (another todo) | 409    | A todo with this title already exists        |
| PATCH with no fields           | 422    | At least one field must be provided          |

## Acceptance Criteria

1. PUT replaces `title` and `completed`; omitting `completed` resets it to `false`.
2. PATCH updates only the provided fields.
3. PATCH with no fields returns 422.
4. `POST /todos/{id}/complete` sets `completed` to `true` and returns the todo.
5. `POST /todos/{id}/incomplete` sets `completed` to `false` and returns the todo.
6. Both convenience endpoints are idempotent.
7. Updating title to a duplicate (case-insensitive, different todo) returns 409.
8. Updating title to whitespace-only returns 422.
9. All update endpoints return 404 for a non-existent id.
10. All update endpoints return 422 for a non-integer id.
11. Title is trimmed on update, same as on create.
