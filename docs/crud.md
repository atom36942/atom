# Generic CRUD

Atom's biggest feature: **create / read / update / delete on any table without writing per-table endpoints**. You pass a `table` name plus data or query params, and the framework validates against the live schema, builds SQL safely, and returns results.

The engine is a set of pure functions in [`function.py`](../function.py) — `func_postgres_create`, `func_postgres_read`, `func_postgres_update`, `func_postgres_delete`, plus `func_postgres_where_build` (filters) and `func_postgres_relation` (joins). Endpoints in `router/my.py`, `router/public.py`, and `router/admin.py` wrap them with different permission scopes.

---

## Endpoints by scope

| Endpoint | Scope | Notes |
|----------|-------|-------|
| `/public/object-create` · `/public/object-read` | Anyone | Only tables in `config_table_public_create_enable` / `_read_enable`. |
| `/my/object-create` · `/object-read` · `/object-update` · `/object-delete` | The caller's **own** rows | Scoped by an ownership column (`created_by_id` / `user_id`). |
| `/my/object-delete-all` · `/object-delete-received*` | The caller's own rows in bulk | Gated by `config_table_my_delete_all*_enable`. |
| `/admin/object-create` · `-read` · `-update` · `-delete` | Any row, any table | Role-restricted (role 1/2). |

The `my` tier automatically stamps and filters by ownership so a user can only touch their own data; the `admin` tier is unrestricted (behind role checks); `public` is read/write on an explicit allow-list only.

---

## Create

`func_postgres_create` inserts one or many rows.

```jsonc
POST /my/object-create?table=test
// single object
{"title": "hello", "type": 1}
// or a batch
{"obj_list": [{"title": "a"}, {"title": "b"}]}
```

- Accepts a single object **or** an `obj_list`; capped at `config_batch_item_limit`.
- Values are serialized/validated against the schema (types, `regex`, mandatory columns).
- The `my` endpoint injects `created_by_id` from the token; server-managed columns in `config_column_admin` are rejected if a client sends them.
- **`mode`** query param: `now` writes immediately; `buffer` appends to the in-memory buffer flushed by `pulse_flush` (see [lifespan.md](lifespan.md)) — use `buffer` for high-volume, low-urgency inserts.
- Optional **`queue`** param routes the create through Redis/RabbitMQ/Kafka/Celery to a background consumer instead of writing inline.

---

## Read

`func_postgres_read` powers `/my/object-read` and `/public/object-read`. Query params:

| Param | Meaning | Example |
|-------|---------|---------|
| `table` | Table to read (validated against schema) | `test` |
| `column` | Columns to return | `id,title` (default `*`) |
| `filter` | List of WHERE conditions (see below) | `["type = 1"]` |
| `order` | Sort | `id desc` (default) |
| `limit` / `page` | Pagination | `limit=20&page=2` |
| `relation` | Join related rows (see below) | — |

Reads fetch `limit + 1` rows internally to compute `has_next_page`:

```jsonc
{"status": 1, "message": {"obj_list": [ … ], "has_next_page": true}}
```

Limits are capped by `config_sql_read_limit_max`.

### Filters (`func_postgres_where_build`)

`filter` is a list of strings `"<column> <operator> <value>"`. The column is validated against the table schema and the value is always **bound as a parameter** (no SQL injection). Supported operators:

| Kind | Operators |
|------|-----------|
| Comparison | `=` `!=` `>` `<` `>=` `<=` (and aliases `eq`, `neq`, `gt`, `lt`, `gte`, `lte`) |
| Null / distinct | `is`, `is not`, `is distinct from`, `is not distinct from` |
| Sets / ranges | `in`, `not in`, `between` |
| Text | `like`, `ilike`, `~`, `~*` (text columns only) |
| Array | `contains`, `overlap`, `any` (array columns) |
| JSON | `contains`, `exists` (jsonb columns) |

Combine conditions with `OR` inside a string, or multiple list items (AND'd):

```jsonc
"filter": ["type = 1", "rating >= 4", "title ilike %atom%"]     // AND'd
"filter": ["status = 1 OR status = 2"]                          // OR
"filter": ["created_at between 2024-01-01 AND 2024-12-31"]      // range
```

### Relations (`func_postgres_relation`)

`relation` fetches related rows in one batched query (avoiding N+1). Each entry names the local key, the related table, and its foreign key; fetch depth is capped by `config_sql_read_relation_fetch_limit_max`. On `public` reads the related table must also be in the read allow-list.

---

## Update

`func_postgres_update` updates existing rows by id.

```jsonc
PUT /my/object-update?table=test
{"obj_list": [{"id": 10, "title": "new title"}]}
```

- Each object must carry its `id`.
- `my` scopes the update to rows the caller owns (`created_by_id`); attempts to set `config_column_admin` fields are rejected, and on the `users` table `config_column_admin_users` (`role`) is blocked too.
- Sensitive user fields (`config_column_single_update`: `password`, `email`, `mobile`, …) must be updated one at a time.
- `updated_at` / `updated_by_id` are maintained automatically.

---

## Delete

`func_postgres_delete` removes rows by id list.

```jsonc
POST /my/object-delete?table=test
{"ids": [10, 11, 12]}
```

- `ids` is a `list:int`, capped at `config_batch_item_limit`.
- `my` deletes only the caller's own rows; `admin` can delete any.
- Rows flagged `is_protected` are shielded, and per-table delete guards (`table_row_delete_disable_all` / `_bulk` in `config_postgres.control`) apply. See [config.md](config.md#control).
- **Bulk own-data** deletes go through `/my/object-delete-all` (tables in `config_table_my_delete_all_enable`) and the `object-delete-received*` variants for message/notification tables.

---

## Group-by reads

`func_postgres_groupby_read` (endpoint `/public/table-groupby`) returns aggregated counts/sums grouped by a column — e.g. counts per `type` — with its own `filter`, `limit`, `page`, `order`, aggregate function, and aggregate column.

---

## Why it's safe

- **Table & column names** are validated against `cache_postgres_schema` (built at startup), so only real columns are usable.
- **Values** are always parameter-bound by `func_postgres_serialize` / `where_build` — never string-interpolated.
- **Access** is layered: table allow-lists (`config_table_*`), ownership scoping (`config_column_ownership`), and restricted-column rejection (`config_column_admin`). See [security.md](security.md).

---

📚 [Back to README](../readme.md)
