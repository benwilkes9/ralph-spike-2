# JTBD 1: Create a Todo

## Job Statement

When I have a new task to remember, I need to create a todo item.

## Endpoint

`POST /todos`

## Request Body

| Field   | Type   | Required | Notes          |
|---------|--------|----------|----------------|
| `title` | string | Yes      | Max 500 chars  |

- `completed` is not accepted on creation; it always defaults to `false`.

## Validation Rules

1. `title` must be present and non-empty.
2. `title` must not be whitespace-only (after trimming).
3. `title` must not exceed 500 characters.
4. `title` must be unique (case-insensitive) across all existing todos.

## Behaviour

- Leading/trailing whitespace in `title` should be trimmed before any validation or storage. All subsequent checks (blank, length, uniqueness) apply to the **trimmed** value.
- On success, return the created todo with its assigned `id`.

## Response

- **201 Created** — returns the full todo object (`id`, `title`, `completed`).

## Error Scenarios

| Condition                  | Status | Detail                                      |
|----------------------------|--------|---------------------------------------------|
| Missing `title`            | 422    | `title` is required                         |
| Empty / whitespace `title` | 422    | `title` must not be blank                   |
| `title` exceeds 500 chars  | 422    | `title` must be 500 characters or fewer     |
| Duplicate title            | 409    | A todo with this title already exists        |

## Acceptance Criteria

1. A valid POST creates a todo and returns 201 with the todo object.
2. The returned `id` is a unique auto-generated integer.
3. `completed` is always `false` on the returned object.
4. Titles differing only by case are rejected as duplicates (409).
5. Whitespace-only titles are rejected (422).
6. Titles over 500 characters are rejected (422).
7. Leading/trailing whitespace is trimmed in the stored title.
