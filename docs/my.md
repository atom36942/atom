# 👤 User-Scoped APIs (`/my/*`) & Ownership Architecture

The `/my/*` router provides self-service CRUD endpoints scoped strictly to the authenticated user's session (`request.state.user["id"]`).

Atom organizes user-scoped actions into a **symmetric two-tier model**:
1. **Creator-Scoped Endpoints (`/my/object-*`):** Operate exclusively on records *created by* the user (`created_by_id`).
2. **Consumer / Assigned Endpoints (`/my/object-*-owned`):** Operate on records *assigned to or received by* the user via a flexible `ownership_column` (e.g. `received_by_id`, `assigned_to_id`).

---

## 📊 Complete CRUD & Ownership Matrix

| Operation | Creator Route (`created_by_id`) | Consumer / Assigned Route (`ownership_column`) | Scope & Description |
| :--- | :--- | :--- | :--- |
| **Create** | `POST /my/object-create` | *(N/A)* | Inserts records and automatically stamps `created_by_id = current_user.id`. |
| **Read (Query)** | `GET /my/object-read` | `GET /my/object-read-owned` | **Creator:** Reads records where `created_by_id = current_user.id`.<br>**Owned:** Reads records where `<ownership_column> = current_user.id` (supports auto mark-as-read). |
| **Update** | `PUT /my/object-update` | *(N/A)* | Updates records where `created_by_id = current_user.id` and stamps `updated_by_id`. |
| **Delete (IDs)** | `POST /my/object-delete` | `POST /my/object-delete-owned` | **Creator:** Deletes specific IDs where `created_by_id = current_user.id`.<br>**Owned:** Deletes specific IDs where `<ownership_column> = current_user.id`. |
| **Delete (All)** | `DELETE /my/object-delete-all` | `DELETE /my/object-delete-owned-all` | **Creator:** Bulk deletes all records where `created_by_id = current_user.id`.<br>**Owned:** Bulk deletes all records where `<ownership_column> = current_user.id`. |
| **User Delete** | `DELETE /my/user-delete?id=<id>` | *(N/A)* | Explicit self-account deletion (`id == current_user.id`, requires `config_is_user_delete = True`). |

---

## 🔍 Detailed Endpoint Comparison

### 1. Read Operations

| Feature | `GET /my/object-read` | `GET /my/object-read-owned` |
| :--- | :--- | :--- |
| **Ownership Column** | Fixed (`created_by_id`) | Dynamic (`ownership_column` query param) |
| **Allowed Columns** | Table must contain `created_by_id` | Must be in `config_column_ownership` |
| **Auto Mark as Read** | ❌ No | ✅ Yes (when `ownership_column="received_by_id"`) |
| **Use Case** | Fetching posts, drafts, or tasks created by user | Fetching inbox messages, notifications, or assigned tasks |

---

### 2. Deletion Operations

| Feature | `POST /my/object-delete` | `POST /my/object-delete-owned` | `DELETE /my/object-delete-all` | `DELETE /my/object-delete-owned-all` | `DELETE /my/user-delete` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Target IDs** | Explicit list of integer `ids` in body | Explicit list of integer `ids` in body | All records matching user ownership | All records matching user ownership | Single `id` query param |
| **Ownership Column** | Fixed (`created_by_id`) | Dynamic (`ownership_column` in body) | Fixed (`created_by_id`) | Dynamic (`ownership_column` in query) | Self ID check (`id == current_user.id`) |
| **Config Whitelist** | None (creator access) | None (consumer access) | `config_table_my_delete_all_allowed` | `config_table_my_delete_owned_all_allowed` | `config_is_user_delete` |
| **Users Table Guard**| ❌ Blocked (use `/my/user-delete`) | ❌ Blocked | ❌ Blocked | ❌ Blocked | ✅ Dedicated Endpoint |

---

## ⚡ Unified 6-Step Route Anatomy

Every endpoint in `/my/*` executes an identical, deterministic sequence of steps:

```python
# 1. Parameter extraction & typing
oq = await app_state.func_request_param_read(request=request, mode="query", ...)

# 2. Batch limit guard (if ID-based)
app_state.func_check_batch_limit(app_state=app_state, items=...)

# 3. Security guards (table whitelists & user policies)
app_state.func_check_table_permission(app_state=app_state, table=..., scope="my", action=...)
app_state.func_check_user_delete_permission(app_state=app_state, table=..., scope=...)

# 4. Schema column existence check
app_state.func_check_table_column_exists(app_state=app_state, table=..., column=..., purpose="ownership tracking")

# 5. Database engine execution
result = await app_state.func_postgres_*(...)

# 6. Standard response format
return {"status": 1, "message": result}
```

---

## 📩 Auto Mark-as-Read on Inbox Reads

When querying `GET /my/object-read-owned` with `ownership_column=received_by_id`, the system automatically invokes `func_postgres_mark_read`:

```python
if oq["ownership_column"] == "received_by_id" and "id" in schema_cols and "read_at" in schema_cols:
    app_state.func_postgres_mark_read(
        client_postgres=app_state.client_postgres,
        table=oq["table"],
        ownership_column=oq["ownership_column"],
        user_id=request.state.user["id"],
        ids=[r.get("id") for r in ol if isinstance(r, dict)]
    )
```
This automatically timestamps `read_at = NOW()` for all returned message/notification IDs without requiring a separate API roundtrip.
