# JTBD 5: Filter, Sort, Search, and Paginate Todos

## Job Statement

When I have many todos, I need to filter, sort, search, and paginate them to find what I need quickly.

## Endpoint

`GET /todos`

This spec extends the base retrieve behaviour defined in `retrieve-todos.md`. When no query parameters are provided, the existing behaviour (return all todos, newest first) is preserved.

## Query Parameters

| Parameter  | Type    | Required | Default     | Notes                                      |
|------------|---------|----------|-------------|--------------------------------------------|
| `completed`| boolean | No       | —           | Filter by completion status                |
| `search`   | string  | No       | —           | Case-insensitive substring match on `title`|
| `sort`     | string  | No       | `id`        | Field to sort by: `id` or `title`          |
| `order`    | string  | No       | `desc`      | Sort direction: `asc` or `desc`            |
| `page`     | integer | No       | `1`         | Page number (1-indexed)                    |
| `per_page` | integer | No       | `10`        | Items per page (1–100)                     |

## Filtering

- `completed=true` returns only completed todos.
- `completed=false` returns only incomplete todos.
- Omitting `completed` returns all todos regardless of status.
- `completed` values other than `true` or `false` return 422.

## Search

- `search` performs a case-insensitive substring match against the `title` field.
- An empty `search` string is treated as no filter (returns all).
- Search is combined with other filters (e.g., `?completed=true&search=buy` returns completed todos containing "buy").

## Sorting

- `sort=id` sorts by `id` (default).
- `sort=title` sorts alphabetically by `title` (case-insensitive).
- `order=asc` sorts ascending; `order=desc` sorts descending (default).
- Invalid `sort` values return 422.
- Invalid `order` values return 422.

## Pagination

- Results are paginated with `page` and `per_page`.
- `page` must be a positive integer (>= 1); invalid values return 422.
- `per_page` must be an integer between 1 and 100 (inclusive); invalid values return 422.
- Requesting a page beyond the last page returns an empty `items` list (not an error).

## Response Format

When any query parameter is provided, the response wraps results in a pagination envelope:

```json
{
  "items": [ ... ],
  "page": 1,
  "per_page": 10,
  "total": 42
}
```

- `items`: array of todo objects for the current page.
- `page`: the current page number.
- `per_page`: the page size used.
- `total`: total number of matching todos (before pagination).

When **no** query parameters are provided, the response remains a plain JSON array for backward compatibility with the base `retrieve-todos.md` spec.

## Error Scenarios

| Condition                        | Status | Detail                                          |
|----------------------------------|--------|-------------------------------------------------|
| `completed` not `true`/`false`   | 422    | `completed` must be true or false               |
| `sort` not `id` or `title`       | 422    | `sort` must be 'id' or 'title'                  |
| `order` not `asc` or `desc`      | 422    | `order` must be 'asc' or 'desc'                 |
| `page` < 1 or not an integer     | 422    | `page` must be a positive integer               |
| `per_page` < 1, > 100, or not int| 422    | `per_page` must be an integer between 1 and 100 |

## Acceptance Criteria

1. `GET /todos?completed=true` returns only completed todos.
2. `GET /todos?completed=false` returns only incomplete todos.
3. `GET /todos?search=buy` returns todos whose title contains "buy" (case-insensitive).
4. Search and filter can be combined.
5. `GET /todos?sort=title&order=asc` returns todos sorted alphabetically ascending by title.
6. Default sort is by `id` descending (newest first), matching base behaviour.
7. Paginated response includes `items`, `page`, `per_page`, and `total`.
8. Requesting a page beyond total results returns empty `items` with correct `total`.
9. `per_page=1` returns one item per page.
10. Invalid query parameter values return 422 with descriptive detail.
11. When no query parameters are provided, response is a plain JSON array (backward compatible).
