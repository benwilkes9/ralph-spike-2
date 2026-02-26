# Data Model: Todo

## Purpose

Define the single resource the API manages.

## Schema

| Field       | Type    | Constraints                        | Default |
|-------------|---------|------------------------------------|---------|
| `id`        | integer | Auto-generated, primary key        | —       |
| `title`     | string  | Required, max 500 chars, unique (case-insensitive), no whitespace-only | —       |
| `completed` | boolean | —                                  | `false` |

## Uniqueness

- Title uniqueness is **case-insensitive**: `"Buy milk"` and `"buy milk"` are considered duplicates.
- Uniqueness is enforced on create and update.

## Storage Rules

- `title` is trimmed of leading/trailing whitespace before storage. All validation (blank, length, uniqueness) is applied to the trimmed value.

## Notes

- No timestamps (`created_at`, `updated_at`) are tracked.
- No soft-delete flag; deletion is permanent.
- Ordering relies on `id` (auto-incrementing integer) as a proxy for creation order.
