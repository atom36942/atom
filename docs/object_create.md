# ➕ Object Create API & Engine (`func_postgres_create`)

The `func_postgres_create` engine handles object/record creation across single-row inserts, bulk batch inserts, and high-throughput background buffering.

---

## 🧠 Major Concepts & Architectural Design

### 1. **Insertion Modes (`mode`)**
* **`now` (Immediate Insert):** Inserts records into PostgreSQL immediately.
  * **Single Object (`len(obj_list) == 1`):** Executes standard `INSERT INTO <table> (...) VALUES (...) RETURNING id` using parameter binding.
  * **Bulk Batch (`len(obj_list) > 1`):** Uses PostgreSQL's high-performance `jsonb_to_recordset($1::jsonb)` to stream up to **5,000 objects per query roundtrip** inside a single transaction with automatic type casting.
* **`buffer` (In-Memory Queueing):** Appends records to `cache_postgres_buffer` for async background flushing (ideal for high-throughput logging, telemetry, or bulk webhooks).
* **`flush` (Buffer Drain):** Drains all queued buffers and executes bulk `jsonb_to_recordset` insertions into PostgreSQL.

### 2. **Data Serialization & Password Hashing**
Before insertion, every batch is processed by `func_postgres_serialize`:
* **Password Fields:** Automatically hashed using `client_password_hasher` (e.g. Argon2/Bcrypt).
* **JSONB Columns:** Dict/List values are serialized to JSON strings.
* **Array Columns:** Arrays (`text[]`, `int[]`, etc.) are converted to PostgreSQL array literals.

### 3. **Validation & Security**
* **Identifier Protection:** All table names and column keys are sanitized against regex `^[a-zA-Z0-9_\s\(\)\-\.]+$`.
* **Regex Rule Enforcement:** Calls `func_regex_check` against schema-defined regex patterns (e.g., email format, phone numbers).
* **Auto `id` Strip:** Removes any client-supplied `id` field to prevent manual primary key manipulation.

---

## ⚙️ Function Signature & Implementation (`function.py`)

```python
async def func_postgres_create(
    *,
    client_postgres: any,
    client_postgres_conn: any = None,
    client_password_hasher: any,
    func_postgres_serialize: callable,
    func_regex_check: callable,
    cache_postgres_schema: dict,
    cache_postgres_buffer: dict,
    config_regex: dict,
    buffer_limit: int,
    mode: str,          # "now" | "buffer" | "flush"
    table: str,
    obj_list: list      # List of dicts to insert
) -> any
```

---

## 🌐 API Endpoint Mappings

| Endpoint | Access Level | Description |
| :--- | :--- | :--- |
| **`POST /public/object-create?table=<tbl>`** | Public | Creates records without requiring user authentication |
| **`POST /my/object-create?table=<tbl>`** | Authenticated User | Creates records and automatically populates `created_by_id` |
| **`POST /admin/object-create?table=<tbl>`** | Admin | Full administrative record creation |

---

## 📝 Request & Response Examples

### Single Record Creation (`mode="now"`)

**cURL Request:**
```bash
curl -X POST "http://localhost:8000/public/object-create?table=test" \
  -H "Content-Type: application/json" \
  -d '{
    "type": 1,
    "title": "New Record",
    "email": "user@example.com",
    "tags": ["tag1", "tag2"],
    "rating": 4.5
  }'
```

**JSON Response:**
```json
{
  "status": 1,
  "message": [10393]
}
```

---

### Bulk Record Insertion (JSON Array)

**cURL Request:**
```bash
curl -X POST "http://localhost:8000/admin/object-create?table=test" \
  -H "Content-Type: application/json" \
  -d '[
    {"type": 1, "title": "Batch Record 1"},
    {"type": 2, "title": "Batch Record 2"},
    {"type": 1, "title": "Batch Record 3"}
  ]'
```

**JSON Response:**
```json
{
  "status": 1,
  "message": [10394, 10395, 10396]
}
```

---

## ⚡ Bulk Insert Performance Mechanics (`jsonb_to_recordset`)

For bulk inserts (`> 1` record), `func_postgres_create` executes the following SQL pattern:

```sql
INSERT INTO "test" ("title", "type", "tags")
SELECT 
    ("title"->>0)::text,
    ("type"->>0)::smallint,
    (SELECT ARRAY(SELECT jsonb_array_elements_text("tags")))::text[]
FROM jsonb_to_recordset($1::jsonb) AS x("title" jsonb, "type" jsonb, "tags" jsonb)
RETURNING id;
```

> **Why this matters:** Instead of sending 5,000 separate `INSERT` queries over the network, 5,000 objects are serialized into a single JSON payload `$1` and ingested natively by PostgreSQL in a single database roundtrip.
