# 🔍 Object Read API & Engine (`func_postgres_read`)

The `func_postgres_read` engine handles table querying, dynamic WHERE filtering (`func_postgres_where_build`), pagination, sorting, field selection, and relational joins (`func_postgres_relation`).

---

## 🧠 Major Concepts & Architectural Design

### 1. **Dynamic WHERE Builder (`func_postgres_where_build`)**
Converts array filter strings into parameterized SQL clauses:
* **Schema Column Validation:** Validates columns against `cache_postgres_schema`.
* **Parameter Binding:** Bound parameter indexing (`$1`, `$2`) to prevent SQL injection.
* **Logical Operator Parsing:** Implicit `AND` across array items and inline `OR` parsing (`"title ilike %A% OR email ilike %B%"`).

### 2. **Datatype-Aware Operators**
* **Numeric:** `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, `between`
* **Text:** `like`, `ilike`, `~` (regex), `~*` (case-insensitive regex)
* **Arrays:** `contains` (`@>`), `overlap` (`&&`), `any` (`= ANY(...)`)
* **JSONB:** `contains` (`@>`), `exists` (`?`)
* **Spatial/GIS:** `point` (`ST_Distance(...) BETWEEN min AND max`)

### 3. **Pagination & Sorting**
* **Limits:** `limit` defaults to 20, max capped by `config_sql_read_limit_max`.
* **Offset Math:** `OFFSET (page - 1) * limit`.
* **Ordering:** `order=col desc, col2 asc` with identifier sanitization.

### 4. **Relational Joins (`func_postgres_relation`)**
Executes sub-queries or aggregations for linked models:
* **Fetch Child/Parent Records:** `fetch|5,id,title`
* **Aggregation Functions:** `count`, `sum`, `avg`, `min`, `max`

---

## ⚙️ Function Signatures (`function.py`)

```python
async def func_postgres_read(
    *,
    client_postgres: any,
    client_password_hasher: any,
    func_postgres_serialize: callable,
    func_postgres_where_build: callable,
    func_postgres_relation: callable,
    cache_postgres_schema: dict,
    config_sql_read_limit_max: int,
    config_sql_read_relation_fetch_limit_max: int,
    table: str,
    filter: list,
    limit: int = 20,
    page: int = 1,
    order: str = "id desc",
    column: str = "*",
    relation: list = None
) -> list
```

---

## 🌐 API Endpoint Mappings

| Endpoint | Access Level | Description |
| :--- | :--- | :--- |
| **`GET /public/object-read?table=<tbl>`** | Public | Read table records with public access filters |
| **`GET /my/object-read?table=<tbl>`** | Authenticated User | Scoped to user's owned records (`created_by_id` or `ownership_column`) |
| **`GET /admin/object-read?table=<tbl>`** | Admin | Unrestricted read query execution |

---

## 📝 Request & Response Examples

### Complex Query Request

**cURL Request:**
```bash
curl -X GET "http://localhost:8000/public/object-read?table=test&limit=10&page=1&order=rating%20desc&filter=%5B%22status%20%3D%201%22%2C%22type%20!%3D%209%22%2C%22rating%20%3E%3D%202%22%2C%22title%20ilike%20%25Title%25%22%5D"
```

**JSON Response:**
```json
{
  "status": 1,
  "message": {
    "obj_list": [
      {
        "id": 10392,
        "type": 1,
        "title": "Title 315",
        "rating": 3.5,
        "status": 1
      }
    ],
    "has_next_page": true
  }
}
```

---

## 📊 Comprehensive Datatype & Operator Reference

| Data Type | Supported Operators | Example Filter Syntax |
| :--- | :--- | :--- |
| **Numeric** | `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `between` | `"status = 1"`, `"type != 9"`, `"rating >= 4"`, `"status in 1\|2\|3"`, `"rating between 1\|5"` |
| **String** | `=`, `!=`, `like`, `ilike`, `~`, `~*` | `"title like %Title%"`, `"email ilike %@example.com"`, `"code ~ ^CODE_"`, `"slug ~* ^slug-"` |
| **Boolean** | `=`, `!=`, `is`, `is not` | `"active = true"`, `"is_verified is true"` |
| **Date/Time** | `>=`, `<=`, `between`, `is null` | `"created_at >= 2026-01-01"`, `"created_at between 2026-01-01\|2026-12-31"` |
| **Array** | `contains`, `overlap`, `any` | `"tag contains tag1"`, `"tag overlap tag1\|tag2"`, `"tag_int any 1"` |
| **JSONB** | `contains`, `exists` | `"metadata contains active\|true\|bool"`, `"metadata exists active"` |
| **Spatial** | `point` | `"coordinate point 80.0\|15.0\|0\|5000"` |
