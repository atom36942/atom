# 🧱 Object APIs

Atom provides reusable object APIs for creating, reading, updating, and deleting rows without writing a route for every table. The same database functions sit behind three access tiers: `public`, `my`, and `admin`.

## Which API should I use?

| Tier | Authentication | Data scope | Operations |
|------|----------------|------------|------------|
| `/public` | Normally none | Tables explicitly allowed by public configuration | Create, read |
| `/my` | Bearer token | Rows owned by the current user | Create, read, update, delete |
| `/admin` | Admin bearer token | Any permitted row in the selected table | Create, read, update, delete |

`public` intentionally has no generic update or delete endpoint. Use `/my` for normal application data owned by a user and reserve `/admin` for trusted management workflows.

All examples assume Atom is running at `http://localhost:8000`, Postgres is configured, and the shipped `test` table is available.

## Common response format

Successful endpoints use Atom's standard envelope:

```json
{
  "status": 1,
  "message": {}
}
```

Read operations return rows and a pagination flag:

```json
{
  "status": 1,
  "message": {
    "obj_list": [{"id": 12, "title": "First object", "type": 1}],
    "has_next_page": false
  }
}
```

## Public objects

Public operations are controlled by `config_table_public_create_enable` and `config_table_public_read_enable`. A table must be explicitly allowed unless the list contains `"*"`.

### Create a public object

```bash
curl -X POST "http://localhost:8000/public/object-create?table=test" \
  -H "Content-Type: application/json" \
  -d '{"title":"Public object","type":1}'
```

Create several objects with `obj_list`:

```bash
curl -X POST "http://localhost:8000/public/object-create?table=test" \
  -H "Content-Type: application/json" \
  -d '{"obj_list":[
    {"title":"Public A","type":1},
    {"title":"Public B","type":2}
  ]}'
```

The table must contain `created_by_id` for ownership tracking. An anonymous request cannot supply an owner, while a request carrying a valid optional token is stamped with that user's ID. Clients cannot set fields listed in `config_column_admin`.

Use `mode=buffer` only for writes that do not need to be visible immediately:

```text
POST /public/object-create?table=test&mode=buffer
```

### Read public objects

```bash
curl -G "http://localhost:8000/public/object-read" \
  --data-urlencode "table=test" \
  --data-urlencode "column=id,title,type,created_at" \
  --data-urlencode 'filter=["type = 1"]' \
  --data-urlencode "order=id desc" \
  --data-urlencode "limit=20" \
  --data-urlencode "page=1"
```

Public reads are not ownership-scoped. Every returned row that matches the filters is visible, so expose only suitable tables and columns. Related tables requested through `relation` must also be allowed for public reads.

## My objects

All `/my/object-*` requests require:

```text
Authorization: Bearer <access_token>
```

The `my` tier protects user-owned data. Creates stamp `created_by_id`; reads, updates, and deletes restrict access to rows owned by the authenticated user.

### Create my object

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"My private object","type":1}'
```

Do not send `created_by_id`; Atom takes it from the token. Tables listed in `config_table_my_create_disable` cannot be created through this endpoint.

For asynchronous processing, add a configured queue:

```text
POST /my/object-create?table=test&queue=redis
```

Supported queue names come from `config_queue_services`. Publishing succeeds only when the matching producer is configured, and a consumer must be running to perform the database write.

### Read my objects

```bash
curl -G "http://localhost:8000/my/object-read" \
  -H "Authorization: Bearer <access_token>" \
  --data-urlencode "table=test" \
  --data-urlencode 'filter=["type = 1","title ilike %private%"]' \
  --data-urlencode "order=id desc" \
  --data-urlencode "limit=20" \
  --data-urlencode "page=1"
```

Atom appends an ownership filter using `created_by_id` by default, so callers cannot read another user's rows by changing their filters. For received objects such as messages or notifications, use `ownership_column=user_id`:

```text
GET /my/object-read?table=notification&ownership_column=user_id
```

The selected ownership column must exist on the table and be included in `config_column_ownership`.

### Update my object

Each update item must include its `id`:

```bash
curl -X PUT "http://localhost:8000/my/object-update?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"id":12,"title":"Updated title","type":2}'
```

Batch updates use `obj_list`:

```json
{
  "obj_list": [
    {"id": 12, "title": "Updated A"},
    {"id": 13, "title": "Updated B"}
  ]
}
```

The table must contain `updated_by_id`, which Atom fills from the token. Non-user tables are additionally restricted by `created_by_id`, so knowing another row's ID is not enough to update it. Server-managed columns are rejected.

User-account updates have extra rules: a user can update only their own row, role changes are blocked, sensitive fields must be changed individually, and email/mobile changes require an OTP when configured.

### Delete my objects

Unlike create, read, and update, the table name belongs in the delete request body:

```bash
curl -X POST "http://localhost:8000/my/object-delete" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"table":"test","ids":[12,13]}'
```

Only rows owned through `created_by_id` are deleted. Protected rows and table-level delete controls still apply. Account hard deletion also requires `config_is_enable_user_delete = 1`, accepts only the caller's user ID, and cannot delete multiple user rows.

`DELETE /my/object-delete-all?table=test` removes all rows created by the current user, but only for tables allowed by `config_table_my_delete_all_enable`. Received rows use `/my/object-delete-received` or `/my/object-delete-received-all` and are scoped by `user_id`.

## Admin objects

Admin object APIs require an authorized bearer token according to their `config_api` policies. They are not ownership-scoped and therefore need stricter operational controls.

### Create as admin

```bash
curl -X POST "http://localhost:8000/admin/object-create?table=test" \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Admin-created object","type":1}'
```

Atom stamps `created_by_id` with the acting administrator. The endpoint also accepts an `obj_list` body and `mode=buffer`.

### Read as admin

```bash
curl -G "http://localhost:8000/admin/object-read" \
  -H "Authorization: Bearer <admin_access_token>" \
  --data-urlencode "table=test" \
  --data-urlencode 'filter=["type in (1,2)"]' \
  --data-urlencode "column=id,title,type,created_by_id" \
  --data-urlencode "order=id desc" \
  --data-urlencode "limit=50" \
  --data-urlencode "page=1"
```

Admin reads can return rows belonging to any user. They also accept `db=<name>` for a configured named PostgreSQL read pool; omit it to use the primary database.

### Update as admin

```bash
curl -X PUT "http://localhost:8000/admin/object-update?table=test" \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"id":12,"title":"Corrected by admin"}'
```

Admin updates are not filtered by the original owner. Atom stamps `updated_by_id` with the acting administrator. Password changes must contain exactly `id` and `password`; configured OTP rules can also apply to administrator changes of a user's email or mobile number.

### Delete as admin

```bash
curl -X POST "http://localhost:8000/admin/object-delete" \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"table":"test","ids":[12,13]}'
```

Admin delete is not ownership-scoped, but it still honors protected-row and table delete safeguards. User hard deletion remains disabled unless `config_is_enable_user_delete = 1`.

## Read options shared by the tiers

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `table` | Database table | `test` |
| `column` | Comma-separated returned columns | `id,title,type` |
| `filter` | JSON list of conditions | `["type = 1"]` |
| `order` | Sort expression | `id desc` |
| `limit` | Rows per page | `20` |
| `page` | One-based page number | `1` |
| `relation` | JSON list of relation expressions | See [Reading Objects](read.md#relations) |
| `db` | Named read database; public/admin only | `analytics` |

Supported filters include comparisons (`=`, `!=`, `>`, `>=`), sets (`in`, `not in`), ranges (`between`), null checks, text matching (`like`, `ilike`), arrays, and JSONB operations. Multiple list entries are combined with `AND`; use `OR` within one entry.

## Important safeguards

- Request batches are capped by `config_batch_item_limit`.
- Read limits are capped by `config_sql_read_limit_max`.
- Table and column names are validated against the cached schema.
- Filter values are bound as SQL parameters.
- `config_column_admin` protects server-managed fields.
- `is_protected` and `config_postgres["control"]` can block deletion.
- `config_api` controls tokens, roles, user status checks, caching, and rate limits for each route.

For complete filter, ordering, pagination, and relation syntax, continue with [Reading Objects](read.md). For internal behavior, see [Generic CRUD](crud.md), and for access-control details, see [Security Model](security.md).

---

📚 [Back to README](../readme.md)
