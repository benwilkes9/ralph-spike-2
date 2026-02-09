# JTBD 2: Retrieve Todos

## Job Statement

When I want to see what tasks I have, I need to retrieve my todos.

## Endpoints

### List All Todos

`GET /todos`

#### Behaviour

- Returns all todos ordered by newest first (descending `id`).
- No pagination, filtering, or sorting parameters.
- Returns an empty list `[]` if no todos exist.

#### Response

- **200 OK** — returns a JSON array of todo objects.

### Get Single Todo

`GET /todos/{id}`

#### Behaviour

- Returns the todo matching the given `id`.

#### Response

- **200 OK** — returns a single todo object (`id`, `title`, `completed`).

#### Error Scenarios

| Condition       | Status | Detail                          |
|-----------------|--------|---------------------------------|
| `id` not found  | 404    | Todo not found                  |
| `id` not valid  | 422    | `id` must be a positive integer |

## Acceptance Criteria

1. `GET /todos` returns 200 with all todos, newest first.
2. `GET /todos` returns 200 with `[]` when no todos exist.
3. `GET /todos/{id}` returns 200 with the matching todo.
4. `GET /todos/{id}` returns 404 when the id does not exist.
5. `GET /todos/{id}` with a non-integer id returns 422.
6. Newest-first ordering is based on descending `id`.
