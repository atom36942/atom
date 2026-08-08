# 🗃️ Generic CRUD & Object APIs

Atom's core database capability allows you to **create, read, update, and delete rows across any database table without writing per-table endpoint boilerplate**. You supply the `table` name along with payload data or query parameters, and the framework validates against the active schema, builds bound SQL queries safely, and returns standard responses.

The generic CRUD engine consists of pure functions in [`function.py`](../function.py):
- **`func_postgres_create`** — Row insertion engine (supports single objects, batch `obj_list`, buffered writes, and background queue routing).
- **`func_postgres_read`** — Query engine with dynamic filtering, sorting, pagination, and relational joins.
- **`func_postgres_where_build`** — SQL `WHERE` clause builder with parameter binding and rich filter operators.
- **`func_postgres_relation`** — Relational join engine (avoids N+1 query overhead).
- **`func_postgres_update`** — Row update engine with ownership verification and column safeguards.
- **`func_postgres_delete`** — Row deletion engine with protected row guards and table-level controls.
- **`func_postgres_groupby_read`** — Group-by aggregation engine (`/public/table-groupby`).

Endpoints in `router/public.py`, `router/my.py`, and `router/admin.py` wrap these functions across three distinct access tiers.

---

## 🏛️ Access Tiers & Permission Scopes

| Tier | Endpoints | Authentication | Data Scope & Permissions |
| :--- | :--- | :--- | :--- |
| **/public** | `/public/object-create`<br>`/public/object-read`<br>`/public/table-groupby` | None (or optional token) | Operates strictly on tables explicitly enabled in `config_table_public_create_enabled` / `config_table_public_read_enabled`. No update or delete endpoints exist in this tier. |
| **/my** | `/my/object-create`<br>`/my/object-read`<br>`/my/object-update`<br>`/my/object-delete`<br>`/my/object-delete-all` | Bearer Token (Required) | Scoped strictly to rows **owned by the authenticated user** (matching `created_by_id` or `ownership_column`). |
| **/admin** | `/admin/object-create`<br>`/admin/object-read`<br>`/admin/object-update`<br>`/admin/object-delete` | Admin Token (Role 1/2) | Unrestricted access across any table or row (bypasses ownership checks behind strict role checks). |

---

## 📋 Common Response Format

All Object API endpoints return Atom's standard response envelope:

```json
{
  "status": 1,
  "message": {}
}
```

Read operations return rows inside `obj_list` along with a pagination flag:

```json
{
  "status": 1,
  "message": {
    "obj_list": [
      {"id": 12, "title": "First object", "type": 1}
    ],
    "has_next_page": false
  }
}
```

---

## ➕ Create Operations (`func_postgres_create`)

Inserts one or more rows into the target table.

### Endpoint Usages:
- **`POST /public/object-create?table=<name>`**
- **`POST /my/object-create?table=<name>`**
- **`POST /admin/object-create?table=<name>`**

### Request Examples:

**Single Object:**
```bash
curl -X POST "http://localhost:8000/my/object-create?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "hello atom", "type": 1}'
```

**Batch Creation (`obj_list`):**
```bash
curl -X POST "http://localhost:8000/my/object-create?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"obj_list": [{"title": "item A"}, {"title": "item B"}]}'
```

### Key Creation Options:
- **Batch Limit**: `obj_list` size is capped by `config_batch_item_limit`.
- **Ownership Stamping**: The `/my` tier automatically stamps `created_by_id` from the caller's JWT token. Server-managed columns in `config_column_admin` are rejected if sent by clients.
- **Write Buffer (`mode=buffer`)**:
  ```text
  POST /my/object-create?table=test&mode=buffer
  ```
  Appends writes to the in-memory buffer flushed periodically by `func_postgres_buffer_flush_periodic_task` (see **[buffer.md](buffer.md)**).
- **Background Queue (`queue=<provider>`)**:
  ```text
  POST /my/object-create?table=test&queue=redis
  ```
  Routes creation requests asynchronously through Redis, RabbitMQ, Kafka, or Celery queues (see **[queue.md](queue.md)**).

---

## 🔍 Read Operations (`func_postgres_read`)

Queries rows with filtering, pagination, sorting, field selection, and relational joins.

### Endpoint Usages:
- **`GET /public/object-read`**
- **`GET /my/object-read`**
- **`GET /admin/object-read`**

### Query Parameters:

| Parameter | Purpose | Example |
| :--- | :--- | :--- |
| `table` | Target database table (validated against schema) | `table=test` |
| `column` | Comma-separated columns to return (defaults to `*`) | `column=id,title,type` |
| `filter` | JSON list of WHERE filter expressions | `filter=["type = 1", "rating >= 4"]` |
| `order` | Sorting clause | `order=id desc` |
| `limit` / `page` | Pagination limit and 1-based page number | `limit=20&page=1` |
| `relation` | Relational join definitions | See **[read.md](read.md)** |
| `ownership_column` | Scopes `/my/object-read` to received rows (e.g. `user_id`) | `ownership_column=user_id` |
| `db` | Named PostgreSQL read pool (public/admin only) | `db=read` |

### Filter Syntax & Operators (`func_postgres_where_build`):

Filter strings follow `"<column> <operator> <value>"`. Values are always parameter-bound to prevent SQL injection.

| Operator Group | Supported Operators | Example Syntax |
| :--- | :--- | :--- |
| **Comparison** | `=`, `!=`, `>`, `<`, `>=`, `<=` (or `eq`, `neq`, `gt`, `lt`, `gte`, `lte`) | `"type = 1"` |
| **Null & Distinct** | `is`, `is not`, `is distinct from`, `is not distinct from` | `"deleted_at is null"` |
| **Sets & Ranges** | `in`, `not in`, `between` | `"status in (1, 2)"`, `"created_at between 2024-01-01 AND 2024-12-31"` |
| **Text Matching** | `like`, `ilike`, `~`, `~*` | `"title ilike %atom%"` |
| **Array Columns** | `contains`, `overlap`, `any` | `"tags contains ['python']"` |
| **JSONB Columns** | `contains`, `exists` | `"meta contains {\"role\": \"user\"}"` |

Multiple filter items in the array are **AND'd** together. Use `OR` inside a single string item (e.g. `"status = 1 OR status = 2"`).

### Group-By Aggregations (`/public/table-groupby`):
Performs aggregated counts and sums grouped by a column:
```text
GET /public/table-groupby?table=test&group_by=type&aggregate_func=count
```

---

## ✏️ Update Operations (`func_postgres_update`)

Updates existing rows by `id`.

### Endpoint Usages:
- **`PUT /my/object-update?table=<name>`**
- **`PUT /admin/object-update?table=<name>`**

### Request Examples:

**Single Update:**
```bash
curl -X PUT "http://localhost:8000/my/object-update?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"id": 12, "title": "Updated title", "type": 2}'
```

**Batch Update:**
```json
{
  "obj_list": [
    {"id": 12, "title": "Updated item A"},
    {"id": 13, "title": "Updated item B"}
  ]
}
```

### Key Update Rules:
- **ID Required**: Every item in payload must include its primary key `id`.
- **Ownership Check**: The `/my` tier ensures `created_by_id` matches the caller's user ID.
- **Single-Update Fields**: Sensitive fields in `config_column_single_update` (`password`, `email`, `mobile`) must be updated individually.
- **Role Guard**: Updating `role` on `users` table via `/my` endpoint is blocked (`config_column_admin_users`).
- **Auto Audit Columns**: `updated_at` and `updated_by_id` are populated automatically.

---

## 🗑️ Delete Operations (`func_postgres_delete`)

Deletes rows by ID.

### Endpoint Usages:
- **`POST /my/object-delete`**
- **`POST /admin/object-delete`**
- **`DELETE /my/object-delete-all?table=<name>`**
- **`DELETE /my/object-delete-received`** / **`object-delete-received-all`**

### Request Example:
```bash
curl -X POST "http://localhost:8000/my/object-delete" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"table": "test", "ids": [12, 13]}'
```

### Delete Safeguards:
- **Protected Rows**: Rows flagged `is_protected` cannot be deleted (`is_protected_delete_disabled`).
- **User Account Hard Delete**: Deleting user accounts requires `config_is_user_delete = 1`.
- **Table Delete Guards**: `table_row_delete_disable_all` and `table_row_delete_disable_bulk` protect critical system tables.
- **Delete-All Enable**: Bulk table deletion via `/my/object-delete-all` requires explicit configuration in `config_table_my_delete_all_enabled`.

---

## 🛡️ Security & Integrity Safeguards

1. **Schema Validation**: Table and column names are validated against `cache_postgres_schema` (built on startup). Unknown tables or columns are rejected before SQL generation.
2. **SQL Injection Immunity**: All filter and payload values are bound as query parameters via `func_postgres_serialize` and `func_postgres_where_build`.
3. **Column Allow-Lists & Block-Lists**: Server-managed system fields (`created_at`, `role`, `verified_at`) in `config_column_admin` are blocked from user writes.
4. **Ownership Enforcement**: `/my` endpoints enforce ownership filters so users cannot read, modify, or delete another user's rows.

---

## 📚 Related Documentation

- **[read.md](read.md)** — Complete guide to query filtering, pagination, field selections, and relational joins.
- **[buffer.md](buffer.md)** — Asynchronous in-memory write buffer and flush loops (`mode=buffer`).
- **[queue.md](queue.md)** — Background worker queues (`queue=redis`, `queue=rabbitmq`, etc.).
- **[security.md](security.md)** — Production security model, role checks, and column protection rules.

---

📚 [Back to README](../readme.md)
