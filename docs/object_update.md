# ✏️ Object Update API & Engine (`func_postgres_update`)

The `func_postgres_update` engine performs high-speed bulk record updates using PostgreSQL `CASE WHEN` SQL expressions, supporting ownership verification and dynamic field serialization.

---

## 🧠 Major Concepts & Architectural Design

### 1. **Bulk CASE-Statement Update Architecture**
When updating multiple records, `func_postgres_update` constructs a single `UPDATE` query using SQL `CASE` statements. This allows updating different values across hundreds or thousands of rows in **a single database roundtrip**:

```sql
UPDATE "test" 
SET 
  "title" = CASE WHEN "id"=$1::bigint THEN $2 WHEN "id"=$3::bigint THEN $4 ELSE "title" END,
  "rating" = CASE WHEN "id"=$1::bigint THEN $5 WHEN "id"=$3::bigint THEN $6 ELSE "rating" END
WHERE "id" IN ($1::bigint, $3::bigint) AND "created_by_id"=$7
RETURNING id;
```

### 2. **Batch Chunking & Parameter Limit Calculations**
PostgreSQL has a bound parameter limit ($65,535). `func_postgres_update` dynamically calculates safe batch sizes:
$$\text{actual\_batch\_size} = \max\left(1, \frac{5000 - \text{owner\_flag}}{(2 \times N_{\text{update\_cols}}) + 1}\right)$$
This guarantees bulk update queries never crash due to parameter limit overflow.

### 3. **Ownership Scoping (`created_by_id`)**
* When called via user scope (`/my/object-update`), the system injects `AND "created_by_id" = $N` into the `WHERE` clause.
* Attempts by users to update rows they do not own will fail or return `0` updated rows safely.

### 4. **Validation & Keys Consistency**
* Every object in `obj_list` MUST contain the primary key `"id"`.
* All objects in a bulk batch MUST contain identical keys to ensure uniform `CASE` statement construction.
* Protected tables (e.g. `spatial_ref_sys`) are blocked.

---

## ⚙️ Function Signature (`function.py`)

```python
async def func_postgres_update(
    *,
    client_postgres: any,
    client_postgres_conn: any = None,
    client_password_hasher: any,
    func_postgres_serialize: callable,
    func_regex_check: callable,
    cache_postgres_schema: dict,
    config_regex: dict,
    table: str,
    obj_list: list,            # List of dicts (must include "id")
    created_by_id: int = None  # User ID scope (None for Admin)
) -> any
```

---

## 🌐 API Endpoint Mappings

| Endpoint | Access Level | Ownership Scoping |
| :--- | :--- | :--- |
| **`PUT /my/object-update?table=<tbl>`** | Authenticated User | Restricted to rows where `created_by_id = current_user.id` |
| **`PUT /admin/object-update?table=<tbl>`** | Admin | Unrestricted update across all rows |

---

## 📝 Request & Response Examples

### Single Record Update (`PUT /my/object-update`)

**cURL Request:**
```bash
curl -X PUT "http://localhost:8000/my/object-update?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 10392,
    "title": "Updated Title Example",
    "rating": 4.8
  }'
```

**JSON Response:**
```json
{
  "status": 1,
  "message": [10392]
}
```

---

### Bulk Batch Update (`PUT /admin/object-update`)

**cURL Request:**
```bash
curl -X PUT "http://localhost:8000/admin/object-update?table=test" \
  -H "Content-Type: application/json" \
  -d '[
    {"id": 10390, "title": "Batch Update 1", "status": 2},
    {"id": 10391, "title": "Batch Update 2", "status": 2}
  ]'
```

**JSON Response:**
```json
{
  "status": 1,
  "message": [10390, 10391]
}
```
