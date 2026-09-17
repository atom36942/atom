# 🗄️ PostgreSQL, Query Engine, Buffering & Logging

Atom provides a comprehensive database layer powered by **asyncpg**, featuring connection pooling, read replicas, raw SQL query runners, in-memory write buffering, and dedicated audit logging.

---

## 1. Connection Pooling & Read Replicas

Atom manages asynchronous PostgreSQL connection pools initialized during startup in `main.py`.

### Primary Pool (`client_postgres`)
The default pool used for all writes and standard reads:
```bash
config_postgres_url=postgresql://atom:secret@localhost:5432/atom
config_postgres_pool_min_size=5
config_postgres_pool_max_size=20
```
Bound to `app.state.client_postgres` and accessible in routes via `request.app.state.client_postgres`.

### Named Pools & Read Replicas (`client_postgres_dict`)
Configure secondary databases or read replicas by adding suffixes in `.env`:
```bash
config_postgres_url_replica1=postgresql://reader:secret@replica-host:5432/atom
config_postgres_url_analytics=postgresql://analyst:secret@analytics-host:5432/warehouse
```
These are automatically mounted onto `app.state.client_postgres_dict["replica1"]`.
Read queries can route to replicas using the query parameter `?db=replica1`:
```bash
curl "http://localhost:8000/public/object-read?table=products&db=replica1"
```

---

## 2. Declarative Schema Management

When `config_is_postgres_schema_init = True`, Atom inspects and automatically migrates the database schema on startup:
- Creates required PostgreSQL extensions (e.g. `uuid-ossp`, `citext`).
- Creates missing tables declared in `config_postgres["table"]`.
- Adds missing columns and alters types if necessary.
- Installs unique constraints and indexes from `config_postgres["index"]`.
- Seeds the root admin user (`admin` / `role: 1`) and attaches the root protection trigger.

---

## 3. Query Runner & AI SQL Engine (`/admin/query`)

Administrators can execute raw SQL directly across multiple databases:
```bash
curl -X POST "http://localhost:8000/admin/query"   -H "Authorization: Bearer <admin_token>"   -H "Content-Type: application/json"   -d '{"sql": "SELECT count(*) FROM users;", "db": "primary"}'
```

### Multi-Database Querying:
Select the destination database via the `db` parameter:
- `primary` or named replica keys in `client_postgres_dict`.
- `mssql` (if `config_mssql_url` is configured).
- `clickhouse` (if `config_clickhouse_url` is configured).

### Natural Language AI SQL Generation:
When an OpenAI or Gemini API key is configured, Atom can translate natural language into optimized SQL queries using `func_ai_sql_generate`. The helper references the cached schema dictionary (`cache_postgres_schema`) to construct valid, context-aware SQL queries.

---

## 4. In-Memory Write Buffering

Atom can buffer high-volume write requests in application memory and insert them in bulk batches. This drastically reduces database round-trips for non-urgent records.

### The Two Runtime Buffers:
Lifespan initializes two independent buffer dictionaries on `app.state`:
1. **`cache_postgres_buffer_create`**: Holds records submitted via object-create APIs with `mode=buffer`. Flushes to the primary database.
2. **`cache_postgres_buffer_log_api`**: Holds request audit records produced by the HTTP middleware. Flushes to `client_postgres_log_api`.

### Flush Modes:
| Mode | Description |
| :--- | :--- |
| `now` | Validate and insert records immediately into PostgreSQL (default). |
| `buffer` | Validate records and append to memory buffer. Returns immediate ack. |
| `flush` | Internal mode: locks buffer, bulk-inserts all pending records via `COPY` or multi-row `INSERT`, and clears buffer. |

### Periodic Background Flush Loop:
Atom runs a periodic background task (`func_postgres_buffer_flush_periodic_task`) draining both buffers every `config_postgres_buffer_flush_auto_sec` (default 60s). It acquires `postgres_buffer_flush_lock` to serialize flushes and ensure no lost writes.

---

## 5. API Logging & Telemetry (`log_api`)

Atom captures structured telemetry for every incoming request in the `log_api` table:

### Telemetry Captured:
- `created_at`: Timestamp of the request.
- `user_id`: Authenticated user ID (or null).
- `client_ip`: Client IP address.
- `path`: Request path.
- `method`: HTTP method (GET, POST, etc.).
- `status_code`: HTTP response status.
- `response_time_ms`: Execution duration in milliseconds.
- `response_type`: Execution path (`cache_response`, `direct_cache_set`, `background_added`, `error`).
- `request_query`, `request_body`: Input payloads.
- `error`: Exception message and traceback on failures.

### Storing Logs in an Isolated Database:
To keep high-volume log writes from contending with business transactions, route API logs to a dedicated PostgreSQL database:
```bash
# .env
config_postgres_url=postgresql://atom:pass@primary-db:5432/atom
config_postgres_url_logs=postgresql://logger:pass@logs-db:5432/atom_logs
config_postgres_db_log_api=logs
```
Atom automatically resolves `app.state.client_postgres_log_api = app.state.client_postgres_dict["logs"]`, routing log buffer flushes exclusively to the dedicated logging instance.
