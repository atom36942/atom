# 📦 Generic CRUD Engine & Ownership Architecture

Atom provides a powerful, high-performance generic CRUD engine that operates across any PostgreSQL table without requiring individual repetitive boilerplate handlers.

Endpoints are split into **access tiers** (`/my/*`, `/public/*`, `/private/*`, `/admin/*`) backed by strict schema validation, ownership guards, and batch limit controls.

---

## 1. Access Tiers & Scopes

| Scope Tier | Base Path | Target Audience | Ownership Enforcement |
| :--- | :--- | :--- | :--- |
| **User** | `/my/object-*` | Authenticated users | Create stamps the creator; read, update, and delete default to creator ownership and accept an operation-approved `ownership_column`. |
| **Public** | `/public/object-*` | Anonymous / Unauthenticated | Restricted by `config_table_public_read_allowed`. |
| **Private** | `/private/object-*` | Internal microservices / backend | Authenticated via token or internal API key. |
| **Admin** | `/admin/object-*` | Superadmins (`role: 1`) | Unrestricted table access across database. |

---

## 2. The `/my/*` Ownership Matrix

For a focused explanation of ownership conventions, configuration policy, SQL enforcement, and failure behavior, see [ownership.md](ownership.md).

Atom uses ownership-column conventions to scope generic user CRUD without trusting a user ID supplied by the client. `/my/object-read`, `/my/object-update`, `/my/object-delete`, and `/my/object-delete-all` accept an optional `ownership_column` query parameter. It defaults to `created_by_id`. The authenticated user ID always comes from the verified token.

Each operation has its own allowlist:

- `config_column_ownership_read`: columns accepted by `/my/object-read`.
- `config_column_ownership_update`: columns accepted by `/my/object-update`.
- `config_column_ownership_delete`: columns accepted by `/my/object-delete` and `/my/object-delete-all`, and used by internal account-data cleanup to discover user-linked rows.

Create does not accept `ownership_column`; `/my/object-create` always stamps `created_by_id` from the authenticated user.

| Operation | Default ownership (`created_by_id`) | Custom ownership (`ownership_column`) | Description |
| :--- | :--- | :--- | :--- |
| **Create** | `POST /my/object-create` | *(N/A)* | Stamped with `created_by_id = current_user.id`. |
| **Read** | `GET /my/object-read` | `GET /my/object-read?ownership_column=received_by_id` | Query records created by or assigned to current user. |
| **Update** | `PUT /my/object-update` | `PUT /my/object-update?ownership_column=assigned_to_id` | Updates matching owned/assigned records; stamps `updated_by_id`. |
| **Delete (IDs)** | `POST /my/object-delete` | `POST /my/object-delete?ownership_column=received_by_id` | Deletes specific IDs matching ownership. |
| **Delete (All)** | `DELETE /my/object-delete-all` | `DELETE /my/object-delete-all?ownership_column=received_by_id` | Bulk wipes matching user rows (allowlist guarded). |
| **Self Delete** | `POST /my/object-delete` with `table="users"` | *(N/A)* | Self-account deletion (`id == current_user.id`). |

The server validates that the requested ownership column is allowed for that operation and exists on the requested table. It then adds `<ownership_column> = current_user.id` to the SQL condition. A caller may choose the ownership relationship but cannot choose the user ID. Table permissions remain a separate authorization layer.

For reads, table/relation permissions, blocked columns, filters, pagination, and `db` selection still apply. Reading through `received_by_id` also marks fetched records as read when the table has `id` and `read_at` columns; those updates use the primary database.

---

## 3. Record Creation (`POST /*/object-create`)

Inserts single records or bulk batches into PostgreSQL.

### Features:
- **Single or Bulk Payload**: Automatically accepts either a single JSON dictionary or a list under `obj_list`.
- **Batch Limit Protection**: Enforces `config_batch_item_limit` (default 1,000 items) to prevent memory exhaustion.
- **Audit Stamping**: In `/my/object-create`, automatically stamps `created_by_id = current_user.id` and `created_at = now()`.
- **Buffered Writes (`mode=buffer`)**: When `mode=buffer` is supplied, writes append to in-memory `cache_postgres_buffer_create` and flush asynchronously in bulk.

### Request Example:
```bash
# Immediate single insert
curl -X POST "http://localhost:8000/my/object-create?table=tasks"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{"title": "Complete documentation", "priority": 1}'

# Buffered bulk insert
curl -X POST "http://localhost:8000/my/object-create?table=logs&mode=buffer"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{"obj_list": [{"event": "click"}, {"event": "scroll"}]}'
```

---

## 4. Record Reading & Query Engine (`GET /my/object-read`)

The examples below assume `tasks`, `users`, and `comments` tables with the illustrated columns. Adapt table/column names to your schema and permissions. Set `BASE_URL` and `TOKEN` before running authenticated examples:

```bash
BASE_URL=http://localhost:8000
TOKEN='<access-token>'
```

Use `curl -G --data-urlencode` for query parameters containing spaces, JSON, commas, or `%`. Send `filter` and `relation` as JSON arrays, not as raw comma-separated query strings.

### Query parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `table` | `str` | Required | Target table. |
| `column` | `str` | `*` | Comma-separated selected columns, e.g. `id,title,created_by_id`. This is singular `column`, not `columns`. |
| `filter` | JSON list | `[]` | Conditions as strings or structured objects; examples below. |
| `relation` | JSON list of strings | `[]` | Related row fetches or aggregates using the five-part syntax below. |
| `order` | `str` | `id desc` | Comma-separated sort columns and directions, e.g. `priority desc,id asc`. |
| `page` | `int` | `1` | One-based page number; must be positive. |
| `limit` | `int` | `config_sql_read_limit_default` (100) | Positive page size. Requests exceeding `config_sql_read_limit_max` (10,000) are rejected. |
| `db` | `str` | Primary pool | Configured pool name, e.g. `read` for `config_postgres_url_read`. |
| `ownership_column` | `str` | `created_by_id` | `/my/object-read` only: column from `config_column_ownership_read` matched to the logged-in user's ID. |

`/public/object-read` and `/admin/object-read` accept the same parameters except `ownership_column`. Public reads require permitted tables and relations; admin reads require admin authorization and do not add user ownership filtering. Blocked columns cannot be explicitly selected or filtered; `column=*` removes them from results.

### Basic selection, sorting, and pagination

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'column=id,title,priority,created_by_id' \
  --data-urlencode 'order=priority desc,id asc' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'page=2'
```

This returns the second page of tasks created by the logged-in user. If an order omits `id`, the reader adds `id desc` as a tie-breaker when the table has that column. `/my/object-read` returns:

```json
{"status": 1, "message": {"obj_list": [], "has_more": false, "has_next_page": false}}
```

Increment `page` while `has_next_page` is true. These flags indicate another page, not a total count. Public and admin reads return `obj_list` and `has_next_page`; they do not currently include `has_more`.

### Filters: comparisons, text search, lists, ranges, and nulls

Separate list entries are combined with AND. Put spaces between the column, operator, and value. These are supported filter expressions, not arbitrary SQL.

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'filter=["status = pending","priority >= 2","title ilike %report%"]'
```

Replace the `filter` value with any of these JSON examples. Columns must exist and support the operator for their datatype:

| Purpose | `filter` value |
| :--- | :--- |
| Equality / inequality | `["status = pending","priority != 0"]` |
| Numeric comparisons | `["priority >= 2","priority < 5"]` |
| Case-sensitive pattern | `["title like Report%"]` |
| Case-insensitive pattern | `["title ilike %report%"]` |
| IDs in a set | `["id in 1,2,3"]` |
| Exclude IDs | `["id not in 4,5"]` |
| Inclusive range | `["priority between 2 AND 5"]` |
| Missing value | `["completed_at is null"]` |
| Present value | `["completed_at is not null"]` |
| Date/time range | `["created_at >= 2026-09-01T00:00:00Z","created_at < 2026-10-01T00:00:00Z"]` |
| Simple OR | `["status = pending OR status = active","priority >= 2"]` |

For nested logic, use `_and` / `_or` objects. Leaf values use `operator,value`; list/range values in this form use `|` separators:

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'filter=[{"_and":[{"_or":[{"status":"=,pending"},{"status":"=,active"}]},{"priority":">=,2"},{"id":"in,1|2|3"}]}]'
```

For array or JSONB columns, use structured expressions to preserve punctuation:

| Column type / purpose | `filter` value |
| :--- | :--- |
| Array contains all values | `[{"tags":"contains,urgent|work"}]` |
| Array overlaps any value | `[{"tags":"overlap,urgent|work"}]` |
| Array contains one value | `[{"tags":"any,urgent"}]` |
| JSONB contains an object | `[{"metadata":"contains,{\"archived\":false}"}]` |
| JSONB contains a key | `[{"metadata":"exists,archived"}]` |

The server appends the ownership condition on `/my/object-read`; client filters do not replace it. Use structured nested logic rather than SQL parentheses for grouped expressions.

### Relations: five-part syntax

Each `relation` item has this format:

```text
source_col,target_table,target_col,op,val
```

| Part | Meaning | Example |
| :--- | :--- | :--- |
| `source_col` | Column in each base record; include it in `column` if selecting fields. | `created_by_id` |
| `target_table` | Related table to read. | `users` |
| `target_col` | Target column matched to the source value. | `id` |
| `op` | `fetch|N`, `count`, `sum`, `avg`, `min`, or `max`. | `fetch|1` |
| `val` | Fetch columns (comma-separated or `*`); aggregate column (`*` is useful for count). | `id,name` |

The first four commas separate the parts; remaining commas belong to `val`. Related rows are fetched in batches for the base rows. There are no `join_table`, `join_column`, or `join_columns` parameters.

**Fetch the creator of each task (many-to-one):**

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'column=id,title,created_by_id' \
  --data-urlencode 'relation=["created_by_id,users,id,fetch|1,id,name"]'
```

When `target_col` is `id`, a fetched relation is attached as one object (or `null`) under the target table name:

```json
{"id": 12, "title": "Write report", "created_by_id": 7, "users": {"id": 7, "name": "Asha"}}
```

**Fetch up to five comments per task and count all matching comments:**

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'column=id,title' \
  --data-urlencode 'relation=["id,comments,task_id,fetch|5,id,body,task_id","id,comments,task_id,count,*"]'
```

When `target_col` is not `id`, fetched rows appear as a list under the target table name. Aggregates appear as `<target_table>_<operation>`:

```json
{"id": 12, "title": "Write report", "comments": [{"id": 91, "body": "Ready", "task_id": 12}], "comments_count": 1}
```

**Other aggregates**, assuming comments have a numeric `score` column:

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'column=id,title' \
  --data-urlencode 'relation=["id,comments,task_id,sum,score","id,comments,task_id,avg,score","id,comments,task_id,min,score","id,comments,task_id,max,score"]'
```

These add `comments_sum`, `comments_avg`, `comments_min`, and `comments_max`. With no matches, count is `0`, other aggregates are `null`, and a to-many fetch is `[]`.

Relation details:

- `fetch` requires an explicit per-source limit, e.g. `fetch|5`, no higher than `config_sql_read_relation_fetch_limit_max` (100 by default). Related rows are ordered by `id desc` independently of the base `order`.
- Include every `source_col` in the base `column` selection; missing source columns are rejected.
- Base `filter`, `page`, and `limit` select base records, not related rows. Relations do not support their own filter or page parameter.
- Table permissions and blocked-column rules apply. The base ownership filter is not automatically added to related tables; relation rows are selected by the source-to-target key match.
- There are no relation aliases or recursive relation definitions. Fetching the same target table twice overwrites its output key; two aggregates with the same table and operation also share an output key.

### Ownership and database selection

Read received notifications from a configured `read` pool:

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=notification' \
  --data-urlencode 'ownership_column=received_by_id' \
  --data-urlencode 'filter=["read_at is null"]' \
  --data-urlencode 'column=id,title,received_by_id,read_at' \
  --data-urlencode 'db=read' \
  --data-urlencode 'limit=20'
```

`db=read` requires a configured named pool; omit it for the primary pool. Base reads and relations use the selected pool. For `received_by_id`, tables with `id` and `read_at` automatically schedule mark-as-read updates on the primary pool. Include `id` in the projection for that update. The current implementation marks all fetched IDs, including the extra look-ahead row used to detect another page.

### All main parameters together

```bash
curl -G "$BASE_URL/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'ownership_column=assigned_to_id' \
  --data-urlencode 'column=id,title,priority,created_by_id,assigned_to_id' \
  --data-urlencode 'filter=["status = active","priority >= 2"]' \
  --data-urlencode 'relation=["created_by_id,users,id,fetch|1,id,name","id,comments,task_id,count,*"]' \
  --data-urlencode 'order=priority desc,id asc' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'page=1' \
  --data-urlencode 'db=read'
```

### Distinct and group-by (separate admin endpoints)

These are not `object-read` parameters. Use an admin token:

```bash
# Distinct values of one column
curl -G "$BASE_URL/admin/table-column-distinct" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'col=status' \
  --data-urlencode 'order=item asc' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'page=1'

# Count tasks per status
curl -G "$BASE_URL/admin/table-column-groupby" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'table=tasks' \
  --data-urlencode 'col=["status"]' \
  --data-urlencode 'agg=count' \
  --data-urlencode 'agg_col=*' \
  --data-urlencode 'filter=["priority >= 2"]' \
  --data-urlencode 'order=count desc' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'page=1'
```

Both accept optional `db` and `filter`. Distinct takes a string `col`; group-by takes a JSON list `col` and supports `agg=count|sum|avg|min|max`. For a numeric sum, use `agg=sum&agg_col=priority&order=sum desc`.

---

## 5. Record Updating (`PUT /*/object-update`)

Executes single or bulk updates efficiently using dynamic SQL `CASE` statements in a single database round-trip.

### Features:
- **Bulk CASE Updates**: Updates hundreds of distinct records with different values in one atomic statement.
- **Audit Stamping**: Automatically stamps `updated_at = now()` and `updated_by_id = current_user.id`.
- **Ownership Verification**: `/my/object-update` defaults to `created_by_id` and accepts only columns from `config_column_ownership_update`. The selected column is matched to the authenticated user ID.

### Request Example:
```bash
curl -X PUT "http://localhost:8000/my/object-update?table=tasks"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{"obj_list": [
        {"id": 1, "title": "Updated Task 1", "status": "done"},
        {"id": 2, "title": "Updated Task 2", "status": "in_progress"}
      ]}'
```

To update a task assigned to the current user:

```bash
curl -X PUT "http://localhost:8000/my/object-update?table=task&ownership_column=assigned_to_id" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"id": 135, "status": 2}'
```

The effective condition is `id = 135 AND assigned_to_id = current_user.id`. If ownership does not match, the returned updated-ID list does not contain that ID. Supplying an ownership column that is not allowed for updates, or that does not exist on the table, is rejected. For `table=users`, `ownership_column` is not supported; self-update account-ID checks apply instead.

---

## 6. Record Deletion (`POST/DELETE /*/object-delete*`)

Atom supports ID-targeted deletions as well as guarded bulk table purges.

### 1. Delete Specific Records by ID (`POST /my/object-delete`)
Body contains an explicit array of integer `ids`:
```json
{"table": "test", "ids": [1, 2, 3]}
```
For ordinary tables, deletes rows where `id = ANY()` AND `created_by_id = current_user.id` by default. The `users` table follows the account deletion rules below.

### 2. Delete Consumer / Owned Records (`POST /my/object-delete?ownership_column=received_by_id`)
Pass the optional `ownership_column` query parameter to select a column from `config_column_ownership_delete`; it defaults to `created_by_id` when omitted. Keep `table` and `ids` in the JSON body, for example `{"table": "message", "ids": [1, 2, 3]}`. Rows must match both a supplied ID and `<ownership_column> = current_user.id`. For `table="users"`, omit `ownership_column`; the own-account deletion checks apply instead.

### 3. Bulk Wipe User Records (`DELETE /my/object-delete-all`)
Wipes all records belonging to the current user in a table in batches capped by `config_batch_item_limit` (currently 1,000; fallback 5,000 when unset or zero) to prevent database locks and gateway timeouts on very large tables. Guarded by:
- The table must be in `config_table_my_delete_all_allowed`.
- The ownership column must be in `config_column_ownership_delete` and exist in the table.

The optional `ownership_column` query parameter defaults to `created_by_id`. Rows must belong to the logged-in user through the selected column. Bulk deletion of `users` is always rejected.

**Response Format**:
```json
{
  "status": 1,
  "message": {
    "deleted_count": 1000,
    "has_more": true,
    "has_next_page": true
  }
}
```
The client can call the exact same endpoint in a loop while `has_more` is `true`. No extra pagination parameters are needed from the client.

### 4. User Account Deletion

Use `POST /my/object-delete` with `{"table": "users", "ids": [7]}` to delete your own account, or `POST /admin/object-delete` with the same body for administrator user deletion. Both require `config_is_user_delete = True` and exactly one ID. The self-account endpoint also requires that ID to match the logged-in user. Omit `ownership_column` for self-account deletion: supplying it explicitly is rejected, including `created_by_id`.

Set `config_is_user_delete = False` and restart to block user deletion through both flows while retaining ordinary object deletion. `/admin/object-delete` has an in-memory rate limit of 10 requests per 60 seconds.
