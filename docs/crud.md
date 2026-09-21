# 📦 Generic CRUD Engine & Ownership Architecture

Atom provides a powerful, high-performance generic CRUD engine that operates across any PostgreSQL table without requiring individual repetitive boilerplate handlers.

Endpoints are split into **access tiers** (`/my/*`, `/public/*`, `/private/*`, `/admin/*`) backed by strict schema validation, ownership guards, and batch limit controls.

---

## 1. Access Tiers & Scopes

| Scope Tier | Base Path | Target Audience | Ownership Enforcement |
| :--- | :--- | :--- | :--- |
| **User (Creator)** | `/my/object-*` | Authenticated users | Strict: records must match `created_by_id = current_user.id`. |
| **User (Owned)** | `/my/object-*-owned` | Authenticated users | Strict: records must match `<ownership_column> = current_user.id`. |
| **Public** | `/public/object-*` | Anonymous / Unauthenticated | Restricted by `config_table_public_read_allowed`. |
| **Private** | `/private/object-*` | Internal microservices / backend | Authenticated via token or internal API key. |
| **Admin** | `/admin/object-*` | Superadmins (`role: 1`) | Unrestricted table access across database. |

---

## 2. The `/my/*` Ownership Matrix

Atom organizes user-scoped actions into a **symmetric two-tier model**:
1. **Creator Routes (`/my/object-*`)**: For resources created by the user (posts, files, settings).
2. **Consumer / Assigned Routes (`/my/object-*-owned`)**: For resources received by or assigned to the user (inbox messages, tasks, notifications).

| Operation | Creator Route (`created_by_id`) | Consumer Route (`ownership_column`) | Description |
| :--- | :--- | :--- | :--- |
| **Create** | `POST /my/object-create` | *(N/A)* | Stamped with `created_by_id = current_user.id`. |
| **Read** | `GET /my/object-read` | `GET /my/object-read-owned` | Query records created by or assigned to current user. |
| **Update** | `PUT /my/object-update` | *(N/A)* | Updates creator's records; stamps `updated_by_id`. |
| **Delete (IDs)** | `POST /my/object-delete` | `POST /my/object-delete-owned` | Deletes specific IDs matching ownership. |
| **Delete (All)** | `DELETE /my/object-delete-all` | `DELETE /my/object-delete-owned-all` | Bulk wipes matching user rows (allowlist guarded). |
| **Self Delete** | `DELETE /my/user-delete?id=<id>` | *(N/A)* | Self-account deletion (`id == current_user.id`). |

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

## 4. Record Reading & Query Engine (`GET /*/object-read`)

A declarative query engine supporting advanced filtering, column projection, joins, and pagination.

### Query Parameters:
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `table` | `str` | *(Required)* | Target PostgreSQL table name. |
| `columns` | `list:str` | All (safe) | Select specific columns (e.g. `["id", "title", "created_at"]`). |
| `filter` | `list:str` | `[]` | JSON-encoded SQL filter conditions. |
| `order` | `str` | `"id desc"` | Sort clause (e.g. `"created_at desc, id asc"`). |
| `page` | `int` | `1` | Pagination page number. |
| `limit` | `int` | `100` | Results per page (capped by `config_query_limit`). |
| `db` | `str` | Primary | Named database pool key to route query to read replicas. |

### Filter Expressions:
Filters are passed as an array of expressions with SQL comparison operators (`=`, `!=`, `>`, `<=`, `like`, `ilike`, `in`, `is null`, `is not null`):
```bash
curl "http://localhost:8000/my/object-read?table=tasks&filter=["status = 'pending'", "priority >= 2"]"   -H "Authorization: Bearer <token>"
```

### Dynamic Relational Joins:
Read queries can join another table in a single request:
- `join_table`: Table to join.
- `join_column`: Target column in primary table.
- `join_target_column`: Key column in joined table.
- `join_columns`: Selected columns from joined table.

### Distinct & GroupBy Aggregations:
- **Distinct**: `GET /*/object-read-column-distinct?table=tasks&col=status`
- **GroupBy**: `GET /*/object-read-column-groupby?table=tasks&cols=["status"]&agg_col=id&agg_func=count`
*(Sensitive columns like `password` or those in `config_column_read_blocked` are strictly forbidden in projections and aggregations).*

---

## 5. Record Updating (`PUT /*/object-update`)

Executes single or bulk updates efficiently using dynamic SQL `CASE` statements in a single database round-trip.

### Features:
- **Bulk CASE Updates**: Updates hundreds of distinct records with different values in one atomic statement.
- **Audit Stamping**: Automatically stamps `updated_at = now()` and `updated_by_id = current_user.id`.
- **Ownership Verification**: Enforces that every updated record matches `created_by_id = current_user.id` in `/my/*` routes.

### Request Example:
```bash
curl -X PUT "http://localhost:8000/my/object-update?table=tasks"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{"obj_list": [
        {"id": 1, "title": "Updated Task 1", "status": "done"},
        {"id": 2, "title": "Updated Task 2", "status": "in_progress"}
      ]}'
```

---

## 6. Record Deletion (`POST/DELETE /*/object-delete*`)

Atom supports ID-targeted deletions as well as guarded bulk table purges.

### 1. Delete Specific Records by ID (`POST /my/object-delete`)
Body contains an explicit array of integer `ids`:
```json
{"ids": [1, 2, 3]}
```
Deletes rows where `id = ANY()` AND `created_by_id = current_user.id`.

### 2. Delete Consumer / Owned Records (`POST /my/object-delete-owned`)
Deletes rows matching `ownership_column = current_user.id` (e.g. `ownership_column="received_by_id"` for inbox messages).

### 3. Bulk Wipe User Records (`DELETE /my/object-delete-all`)
Wipes all records belonging to the current user in a table in safe batches (default 5,000 rows per request) to prevent database locks and gateway timeouts on very large tables. Guarded by:
- `config_table_my_delete_all_allowed` (allowlist of wipeable creator tables).
- `config_table_my_delete_owned_all_allowed` (allowlist of wipeable owned tables).

**Response Format**:
```json
{
  "status": 1,
  "message": {
    "deleted_count": 5000,
    "has_more": true,
    "has_next_page": true
  }
}
```
The client can call the exact same endpoint in a loop while `has_more` is `true`. No extra pagination parameters are needed from the client.

### 4. Self-Account Deletion (`DELETE /my/user-delete?id=<id>`)
Users can delete their own account when `config_is_user_delete = True`. The endpoint verifies `id == current_user.id` and raises an error on any attempt to delete other accounts. The root user (`id: 1`) is permanently protected by database triggers.
