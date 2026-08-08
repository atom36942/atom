# 🔎 Reading Objects

Atom's generic read APIs support column selection, filters, sorting, pagination, relations, ownership scoping, and optional named PostgreSQL read pools. This guide focuses on how to send those parameters correctly and how Atom interprets them.

## Read endpoints

| Endpoint | Access | Scope |
|----------|--------|-------|
| `GET /public/object-read` | Public by default | Any matching row in a table allowed by `config_table_public_read_enabled` |
| `GET /my/object-read` | Bearer token | Only rows owned by the authenticated user |
| `GET /admin/object-read` | Authorized admin token | Any matching row |

`/public/object-read` and `/admin/object-read` accept the optional `db` parameter for a configured named PostgreSQL read pool. `/my/object-read` always uses the primary database because it also supports ownership behavior such as marking received records as read.

## Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `table` | string | required | Table to query; must exist in the cached primary schema |
| `column` | string | `*` | Comma-separated columns to return |
| `filter` | JSON list | `[]` | Conditions applied to the query |
| `order` | string | `id desc` | Comma-separated sort columns with optional `asc` or `desc` |
| `limit` | integer | `config_sql_read_limit_default` | Rows returned per page |
| `page` | integer | `1` | One-based page number |
| `relation` | JSON list | `[]` | Related fetches or aggregates added to each row |
| `db` | string | primary | Named read pool; public/admin only |
| `ownership_column` | string | `created_by_id` | Ownership field; `/my/object-read` only |

The endpoint fetches one extra row internally and returns:

```json
{
  "status": 1,
  "message": {
    "obj_list": [],
    "has_next_page": false
  }
}
```

## A complete read request

Use `curl -G` with `--data-urlencode` so JSON filters, spaces, `%` wildcards, and relation commas are encoded safely:

```bash
curl -G "http://localhost:8000/my/object-read" \
  -H "Authorization: Bearer <access_token>" \
  --data-urlencode "table=test" \
  --data-urlencode "column=id,title,type,created_at" \
  --data-urlencode 'filter=["type = 1","title ilike %atom%"]' \
  --data-urlencode "order=created_at desc,id desc" \
  --data-urlencode "limit=20" \
  --data-urlencode "page=1"
```

In browser JavaScript, let `URLSearchParams` encode the JSON:

```javascript
const params = new URLSearchParams({
  table: "test",
  column: "id,title,type,created_at",
  filter: JSON.stringify(["type = 1", "title ilike %atom%"]),
  order: "created_at desc,id desc",
  limit: "20",
  page: "1",
});

const response = await fetch(`/my/object-read?${params}`, {
  headers: {Authorization: `Bearer ${accessToken}`},
});
const data = await response.json();
```

Do not build a URL by concatenating raw filter text. Characters such as `+`, `%`, `&`, `[` and spaces can change meaning unless encoded.

## Selecting columns

Use `column=*` for every column or pass a comma-separated list:

```text
column=id,title,type,created_at
```

Selecting only the fields the client needs reduces response size. If a relation uses `id` or another source column, that source column **must** be included in `column`; otherwise Atom returns `relation source column missing from selected columns`.

Column aliases and arbitrary SQL expressions are not supported. Names are treated as identifiers and quoted by Atom.

## Filters

The usual filter format is a JSON list of strings:

```json
["column operator value", "column operator value"]
```

Separate list items are joined with `AND`:

```json
["type = 1", "rating >= 4"]
```

This means `type = 1 AND rating >= 4`.

### Comparison filters

```json
["type = 1"]
["status != archived"]
["rating >= 4"]
["price < 100"]
```

Supported comparison operators and aliases:

| Operation | Operators |
|-----------|-----------|
| Equal | `=`, `==`, `eq` |
| Not equal | `!=`, `<>`, `neq` |
| Greater/less | `>`, `<`, `>=`, `<=`, `gt`, `lt`, `gte`, `lte` |

Values are serialized according to the column's PostgreSQL datatype and passed as bound parameters.

### Text filters

`like`, `ilike`, `~`, and `~*` are available only for text-like columns:

```json
["title like Atom%"]
["title ilike %atom%"]
["username ~ ^atom[0-9]+$"]
["username ~* ^ATOM"]
```

- `like` is case-sensitive pattern matching.
- `ilike` is case-insensitive pattern matching.
- `%` matches any sequence and `_` matches one character for `like`/`ilike`.
- `~` is a case-sensitive PostgreSQL regular expression; `~*` is case-insensitive.

Always URL-encode `%` when sending the query manually.

### Null filters

Use `is` or `is not` with `null`:

```json
["deleted_at is null"]
["verified_at is not null"]
```

PostgreSQL distinct comparisons are also supported:

```json
["status is distinct from null"]
["status is not distinct from active"]
```

Do not use `= null`; SQL null checks require `is null` or `is not null`.

### `IN` and `NOT IN`

Separate values with commas or wrap them in parentheses:

```json
["type in (1,2,3)"]
["status not in (deleted,blocked)"]
```

Atom normalizes comma-separated values and binds each item independently.

### Ranges with `BETWEEN`

```json
["rating between 1 AND 5"]
["created_at between 2026-01-01 AND 2026-12-31"]
```

`BETWEEN` requires two values. The uppercase `AND` shown here is the clearest form and is normalized before binding.

### Combining `OR` and `AND`

Place `OR` inside one list item:

```json
[
  "status = draft OR status = published",
  "created_at >= 2026-01-01"
]
```

This becomes:

```text
(status = draft OR status = published)
AND created_at >= 2026-01-01
```

For repeated `AND` conditions on the same column, use separate list items:

```json
["rating >= 2", "rating <= 5"]
```

### Array filters

Array columns support `contains`, `overlap`, and `any`:

```json
["tags contains (python,fastapi)"]
["tags overlap (python,postgres)"]
["tags any fastapi"]
```

- `contains` requires the stored array to contain all supplied values.
- `overlap` matches when at least one supplied value exists in the stored array.
- `any` checks whether one value is present in the stored array.

Values are converted using the array's element datatype.

### JSONB filters

JSONB columns support `contains` and `exists`:

```json
["metadata contains {\"plan\":\"pro\"}"]
["metadata contains active|true|bool"]
["metadata contains attempts|3|int"]
["metadata exists plan"]
```

`contains` accepts a JSON object/array or the shorthand `key|value|type`, where `type` can be `str`, `int`, `float`, or `bool`. `exists` checks for a top-level JSON key.

When sending JSON inside the filter JSON, use a JSON serializer rather than hand-escaping nested quotes.

### Geographic distance filters

Geography point columns support the explicit dictionary form with `point`:

```json
[
  {
    "location": "point,77.5946|12.9716|0|5000"
  }
]
```

The four values are longitude, latitude, minimum distance in meters, and maximum distance in meters. This example matches points between 0 and 5,000 meters from the supplied coordinates.

## Sorting

Use one or more comma-separated columns:

```text
order=created_at desc
order=status asc,created_at desc,id desc
```

If a direction is omitted, Atom uses ascending order for that column. The default is `id desc`.

Use a deterministic final sort such as `id desc` when paginating rows that may share the same timestamp or status. Only plain column identifiers are intended; arbitrary SQL order expressions are not supported.

## Pagination

`page` is one-based and `limit` must be greater than zero:

```text
limit=20&page=1
limit=20&page=2
```

The effective offset is `(page - 1) × limit`. Atom internally requests `limit + 1` rows so it can set `has_next_page`, then returns only `limit` objects. Requests above `config_sql_read_limit_max` are rejected.

Offset pagination is simple but can shift when rows are inserted or deleted between requests. Use a stable order and consider a custom cursor-based endpoint for very large or frequently changing datasets.

## Relations

Relations attach associated rows or aggregate values to each object after the main query. They are fetched in batches, avoiding one database query per source row.

Each relation is a string with five logical parts:

```text
source_column,target_table,target_column,operation,value
```

Because `value` is the final part, it may itself contain a comma-separated column list.

### Fetch a one-to-many relation

Suppose `test.id` is referenced by `comment_test.test_id`. Fetch up to 10 newest comments for each test row:

```text
id,comment_test,test_id,fetch|10,id,title,created_at
```

Send it as a JSON list:

```bash
curl -G "http://localhost:8000/public/object-read" \
  --data-urlencode "table=test" \
  --data-urlencode "column=id,title" \
  --data-urlencode 'relation=["id,comment_test,test_id,fetch|10,id,title,created_at"]'
```

The output adds a `comment_test` list to each source row:

```json
{
  "id": 12,
  "title": "Parent object",
  "comment_test": [
    {"id": 91, "title": "Newest comment", "created_at": "..."},
    {"id": 88, "title": "Older comment", "created_at": "..."}
  ]
}
```

`fetch|10` is mandatory: every fetch relation needs an explicit per-parent limit, and it cannot exceed `config_sql_read_relation_fetch_limit_max`. Related rows are ordered by `id desc`.

Use `*` to fetch every target column:

```text
id,comment_test,test_id,fetch|10,*
```

Prefer an explicit column list for smaller and more stable responses.

### Fetch a belongs-to relation

If a source row has `created_by_id` pointing to `users.id`, fetch one user:

```text
created_by_id,users,id,fetch|1,id,username
```

When the target column is `id`, Atom attaches one object (or `null`) rather than a list:

```json
{
  "id": 12,
  "created_by_id": 7,
  "users": {"id": 7, "username": "alice"}
}
```

Include `created_by_id` in the main `column` selection because it is the relation's source column.

### Relation aggregates

Supported aggregate operations are `count`, `sum`, `avg`, `min`, and `max`.

Count comments per object:

```text
id,comment_test,test_id,count,*
```

Sum a target column per object:

```text
id,order_item,order_id,sum,amount
```

Aggregates add a field named `<target_table>_<operation>`:

```json
{
  "id": 12,
  "comment_test_count": 4
}
```

`count` returns `0` when no rows match. Other aggregates return `null` when no rows match.

### Send multiple relations

Add multiple strings to the JSON list:

```json
[
  "id,comment_test,test_id,fetch|5,id,title,created_at",
  "id,comment_test,test_id,count,*",
  "created_by_id,users,id,fetch|1,id,username"
]
```

With curl:

```bash
curl -G "http://localhost:8000/admin/object-read" \
  -H "Authorization: Bearer <admin_access_token>" \
  --data-urlencode "table=test" \
  --data-urlencode "column=id,title,created_by_id" \
  --data-urlencode 'relation=["id,comment_test,test_id,fetch|5,id,title,created_at","id,comment_test,test_id,count,*","created_by_id,users,id,fetch|1,id,username"]'
```

### Relation rules and limitations

- The source column must be included in the main result.
- `fetch` always requires `fetch|<limit>`.
- Public reads may relate only to tables allowed by `config_table_public_read_enabled`.
- Relations use the same selected database connection as the main public/admin read.
- Named read databases are expected to share the primary schema used for validation.
- Fetches are one level deep; relation strings do not recursively nest more relations.
- Fetch relations add data under the target table name, so two fetches to the same target table overwrite the same output key.
- Aggregates add `<target_table>_<operation>`, so duplicate table/operation pairs share a key.

For complex nested graphs, custom ordering of related rows, relation-specific filters, or cursor pagination, create a purpose-built endpoint.

## Ownership on `/my/object-read`

Atom automatically appends an ownership condition; a caller-supplied filter cannot remove it.

The default is:

```text
ownership_column=created_by_id
```

For objects received by a user, such as messages or notifications, select:

```text
ownership_column=user_id
```

The chosen column must exist in the table and be included in `config_column_ownership`. When `user_id` is used on a table containing `id` and `read_at`, Atom also schedules those returned objects to be marked as read.

## Named read databases

Public and admin reads can select a pool configured in `config_postgres_url_dict`:

```text
GET /public/object-read?db=read&table=test
GET /admin/object-read?db=analytics&table=test
```

Omit `db` to use `config_postgres_url`. The named database must be present in the runtime pool dictionary, and its relevant tables/columns should match the primary cached schema. See [PostgreSQL](postgres.md) for configuration and connection sizing.

## Common errors

| Error | Likely cause | Fix |
|-------|--------------|-----|
| `invalid filter column` | Filter names a column absent from the selected table | Check `/info` or `/admin/postgres-schema` |
| `invalid operator ... for ...` | Operator is incompatible with the column datatype | Use text operators only on text, array operators on arrays, and JSON operators on JSONB |
| `query limit ... exceeds maximum` | `limit + 1` requested by the route exceeds the configured cap | Choose a smaller page size or review `config_sql_read_limit_max` |
| `relation must have 5 parts` | Relation string is incomplete | Use `source,target_table,target_column,operation,value` |
| `explicit limit required in relation fetch` | Used `fetch` without `|N` | Use `fetch|10` |
| `relation source column missing` | `column` omitted the relation's source field | Add that field to `column` |
| `relation read disabled for table` | Public relation targets a non-public table | Allow it only if the data is safe to expose, or use an authenticated endpoint |
| Empty `/my` result | Rows are not owned through the selected ownership column | Check `created_by_id`/`user_id` and the authenticated user |

## Security and performance guidance

- Prefer `/my/object-read` for user-owned data; do not rely on a client-supplied owner filter.
- Expose only intentional tables through `config_table_public_read_enabled`.
- Select only needed columns and use modest page and relation limits.
- Index columns frequently used for filters, ordering, ownership, and relation target keys.
- Relation fetching avoids N+1 queries but can still return many rows: source page size × relation limit.
- Use a stable order for pagination.
- Keep admin reads behind strong route policies and audit their use.

For the full create/read/update/delete overview and CRUD behavior, see [Object APIs](object.md).

---

📚 [Back to README](../readme.md)
