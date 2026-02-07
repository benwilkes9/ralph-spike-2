# JTBD 4: Delete a Todo

## Job Statement

When a task is no longer relevant, I need to delete a todo.

## Endpoint

`DELETE /todos/{id}`

## Behaviour

- Permanently removes the todo from the database (hard delete).
- The deleted todo's `id` is never reused (standard SQLite auto-increment behaviour).

## Response

- **204 No Content** — empty body on success.

## Error Scenarios

| Condition      | Status | Detail                          |
|----------------|--------|---------------------------------|
| `id` not valid | 422    | `id` must be a positive integer |
| `id` not found | 404    | Todo not found                  |

## Acceptance Criteria

1. Deleting an existing todo returns 204 with no body.
2. The todo is no longer retrievable after deletion.
3. Deleting a non-existent id returns 404.
4. Deleting with a non-integer id returns 422.
