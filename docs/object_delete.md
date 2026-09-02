# 🗑️ Object Delete API & Engine (`func_postgres_delete`)

The `func_postgres_delete` engine handles record deletion by primary keys (`id`) with chunking, schema checking, and ownership scoping.

---

## 🧠 Major Concepts & Architectural Design

### 1. **Batch ID Chunking (`limit_chunk = 5000`)**
To process bulk deletions safely, IDs are split into chunks of 5,000 and executed inside a PostgreSQL transaction using `IN` clause parameter binding:

```sql
DELETE FROM "test" 
WHERE "id" IN ($1, $2, $3, ..., $5000)
```

### 2. **Ownership Scoping (`created_by_id`)**
When called under user scope (`/my/object-delete`), the engine validates that the table contains a `created_by_id` column and appends ownership conditions to the query:

```sql
DELETE FROM "test" 
WHERE "id" IN ($1, $2, $3) AND "created_by_id" = $4
```

This prevents users from deleting rows owned by other users, even if they guess valid record IDs.

### 3. **Safety & Protection Checks**
* **Table Verification:** Validates `table` against `cache_postgres_schema`.
* **Protected System Tables:** Explicitly blocks deletion on system tables such as `spatial_ref_sys`.
* **Primary Key Check:** Ensures the target table has an `id` column defined.

---

## ⚙️ Function Signature (`function.py`)

```python
async def func_postgres_delete(
    *,
    client_postgres: any,
    client_postgres_conn: any = None,
    cache_postgres_schema: dict = None,
    table: str,
    ids: list,                 # List of integer IDs to delete
    created_by_id: int = None  # User ID scope (None for Admin)
) -> int                       # Returns total count of deleted rows
```

---

## 🌐 API Endpoint Mappings

| Endpoint | Access Level | Ownership Restriction | Description |
| :--- | :--- | :--- | :--- |
| **`POST /my/object-delete`** | User | `created_by_id = current_user.id` | Deletes owned domain records by ID list (`{"table": "...", "ids": [...]}`) |
| **`POST /admin/object-delete`** | Admin | None | Unrestricted deletion by ID list (`{"table": "...", "ids": [...]}`) |
| **`DELETE /my/object-delete-all?table=<tbl>`** | User | `created_by_id = current_user.id` | Deletes all records owned by current user |
| **`POST /my/object-delete-owned`** | User | `<ownership_column> = current_user.id` | Deletes rows by ID via any ownership column |
| **`DELETE /my/object-delete-owned-all?table=<tbl>&ownership_column=<col>`**| User | `<ownership_column> = current_user.id` | Drains all rows scoped to that column |
| **`DELETE /my/user-delete?id=<user_id>`** | User | Self-account only (`id == current_user.id`) | Deletes user's own account (requires `config_is_user_delete`) |
| **`DELETE /admin/user-delete?id=<user_id>`** | Admin | None | Deletes specific user account by ID (requires `config_is_user_delete`) |

---

## 📝 Request & Response Examples

### Delete Specific IDs (`DELETE /my/object-delete`)

**cURL Request:**
```bash
curl -X DELETE "http://localhost:8000/my/object-delete?table=test&ids=10390,10391" \
  -H "Authorization: Bearer <access_token>"
```

**JSON Response:**
```json
{
  "status": 1,
  "message": 2
}
```

---

### Delete All User Owned Records (`DELETE /my/object-delete-all`)

**cURL Request:**
```bash
curl -X DELETE "http://localhost:8000/my/object-delete-all?table=test" \
  -H "Authorization: Bearer <access_token>"
```

**JSON Response:**
```json
{
  "status": 1,
  "message": "deleted"
}
```
