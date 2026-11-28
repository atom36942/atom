# Ownership and User-Scoped CRUD

Atom's `/my/object-*` endpoints let an authenticated user operate on rows connected to that user through a conventional ownership column. Ownership is enforced by PostgreSQL conditions on the server; frontend checks are only user-interface behavior.

## Core rule

The client may select an allowed ownership relationship, but it never supplies the owner ID. Atom reads the current user ID from the verified access token and applies this condition:

```sql
WHERE "<ownership_column>" = <authenticated_user_id>
```

For example, this request:

```http
PUT /my/object-update?table=task&ownership_column=assigned_to_id
```

with body:

```json
{"id": 135, "status": 2}
```

is effectively scoped as:

```sql
UPDATE task
SET status = 2, updated_by_id = <authenticated_user_id>
WHERE id = 135
  AND assigned_to_id = <authenticated_user_id>
RETURNING id;
```

Choosing `assigned_to_id` therefore does not allow a caller to update rows assigned to another user.

## CRUD behavior

| Operation | Endpoint | Ownership behavior |
|---|---|---|
| Create | `POST /my/object-create` | Always stamps `created_by_id` from the authenticated user. It does not accept `ownership_column`. |
| Read | `GET /my/object-read` | Defaults to `created_by_id`; another column's `ownership` must list `read`. |
| Update | `PUT /my/object-update` | Defaults to `created_by_id`; another column's `ownership` must list `update`. |
| Delete IDs | `POST /my/object-delete` | Defaults to `created_by_id`; another column's `ownership` must list `delete`. `?mode=soft` sets `deleted_at` instead of deleting. |
| Delete all | `DELETE /my/object-delete-all` | The same `delete` owners, plus `control.my_delete_all`. |

All ownership-aware endpoints validate that the selected column exists on the requested table. Omitting `ownership_column` consistently means `created_by_id`. Each action also needs the table in its `control` list (`my_create`, `my_read`, `my_update`, `my_delete`, `my_delete_all`), else 403 ([control](config.md#control)).

## Configuration

An owner column is a column key in the schema, per table: `ownership` lists the `/my` actions (`read`, `update`, `delete`) that may find a user's rows by it. `created_by_id` is always the owner and takes no key.

```python
"task": {"column": [
...
{"name": "created_by_id", "datatype": "bigint", "index": ["btree(created_by_id,id)"]},
{"name": "assigned_to_id", "datatype": "bigint", "index": ["btree(assigned_to_id)"], "ownership": ["read", "update"]},
]},
```

Atom's: `message.received_by_id` and `notification.received_by_id` `["read", "delete"]`; `log_users_password.user_id` and `log_users_delete.user_id` `["read"]`.

The users-delete worker uses only the `delete` owners (with `created_by_id`) to find a deleted user's rows for soft deletion and restoration, in master's tables that have `deleted_at` (never `users` or `log_users_delete`; other databases are not touched). Columns approved only for reading or updating do not link rows to a user for this cleanup.

List an action only when the column's meaning grants it. For example:

- `created_by_id` means the user created the row.
- `assigned_to_id` means the user is responsible for the row and may read or update it.
- `received_by_id` means the user received the row; it may grant read/delete without granting update.
- `user_id` is read-only because its meaning may be broader than ownership.

## API examples

Read assigned tasks:

```bash
curl -G "http://localhost:8000/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=task' \
  --data-urlencode 'ownership_column=assigned_to_id'
```

Update an assigned task:

```bash
curl -X PUT "http://localhost:8000/my/object-update?table=task&ownership_column=assigned_to_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": 135, "status": 2}'
```

Delete received notifications:

```bash
curl -X POST "http://localhost:8000/my/object-delete?ownership_column=received_by_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"table": "notification", "ids": [10, 11]}'
```

## Responses and authorization failures

- Update returns the IDs actually updated. The caller should verify that every expected ID is present.
- ID deletion reports the number of rows actually deleted.
- An allowed ownership column with a nonmatching row updates or deletes no row.
- A column that is not `created_by_id` and whose `ownership` does not list the action on that table is refused (403).
- A column absent from the requested table is refused.

Batch updates and deletes can affect only the requested IDs that match the ownership condition. Clients that require all-or-nothing business behavior should verify the returned IDs/count and treat a partial result as a failed business operation.

## Special cases

- `users`: the object routes refuse it; a user changes or deletes their own account with `/my/user-update` and `/my/user-delete` (account-ID checks, no `ownership_column`).
- `received_by_id` reads: when the table also has `id` and `read_at`, the rows returned are marked as read in the background, on the database they were read from.
- Queued updates preserve the validated ownership column in the queued payload.
- `/private/*` and `/admin/*` have different trust models and do not inherit `/my/*` ownership behavior.

## Security guidance

1. Treat `ownership` as authorization policy, not merely schema metadata.
2. Keep ownership meanings consistent across tables.
3. Never accept a user ID as a substitute for the authenticated token ID.
4. Continue using route-specific table permissions, blocked-column rules, restricted update fields, and batch limits; ownership is one authorization layer, not the entire security model.
5. Keep frontend ownership checks for usability only. The backend SQL condition remains authoritative.

See [crud.md](crud.md) for the complete generic CRUD engine and [config.md](config.md) for the broader configuration reference.
