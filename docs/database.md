# 🗄️ PostgreSQL, Query Engine, Buffering & Logging

Atom provides a comprehensive database layer powered by **asyncpg**, featuring connection pooling, read replicas, raw SQL query runners, in-memory write buffering, and dedicated audit logging.

---

## 1. Connection Pooling & Read Replicas

Atom manages asynchronous PostgreSQL connection pools initialized during startup in `main.py`.

### Databases by name (`client_postgres_dict`)
Every database is one `.env` line, `config_postgres_url_<name>`. `master` is required and is the default database (writes, users, config, schema init):
```bash
config_postgres_url_master=postgresql://atom:secret@localhost:5432/atom
config_postgres_url_replica1=postgresql://reader:secret@replica-host:5432/atom
config_postgres_url_analytics=postgresql://analyst:secret@analytics-host:5432/warehouse
config_postgres_pool_min_size=5
config_postgres_pool_max_size=20
```
Each name becomes a pool in `app.state.client_postgres_dict` (for example `client_postgres_dict["master"]`) with its schema in `app.state.cache_postgres_schema_dict`. Code that always uses the main database reads `client_postgres_dict["master"]`. Every URL needs a name: an unsuffixed `config_postgres_url` (also `config_redis_url`, `config_clickhouse_url`, `config_mssql_url`) or an empty `config_postgres_url_` stops startup.
Routes flagged `"is_connection_param": True` in `config_api` take `?connection=<name>`; the middleware sets `request.state.client_postgres` and `request.state.cache_postgres_schema` (master when `connection` is omitted, 404 for an unknown name). Other routes always use master and reject `?connection=` with 400:
```bash
curl "http://localhost:8000/public/object-read?table=products&connection=replica1"
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

## 3. Query Runner & AI SQL Engine (`/admin/postgres-query-runner-*`)

Administrators can execute raw SQL. Reads accept `?connection=<name>` to pick a database; writes always use master:
```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-read?connection=replica1" -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" -d '{"sql": "SELECT count(*) FROM users;"}'
```
MSSQL and ClickHouse have their own routes: `/admin/mssql-query-runner-*` and `/admin/clickhouse-query-runner-*`. They take body param `connection` (default `master`) to pick a server from `config_mssql_url_<name>` or `config_clickhouse_url_<name>`; an unknown name returns 404.

### Natural Language AI SQL Generation:
When an OpenAI or Gemini API key is configured, Atom can translate natural language into optimized SQL queries using `func_ai_sql_generate`. The helper references the cached schema dictionary (`cache_postgres_schema`) to construct valid, context-aware SQL queries.

---

## 4. In-Memory Write Buffering

Atom can buffer high-volume write requests in application memory and insert them in bulk batches. This drastically reduces database round-trips for non-urgent records.

### The Two Runtime Buffers:
Lifespan initializes two independent buffer dictionaries on `app.state`:
1. **`buffer_postgres_create`**: Holds records submitted via object-create APIs with `mode=buffer`. Flushes to master.
2. **`buffer_postgres_log_api`**: Holds request audit records produced by the HTTP middleware. Flushes to `client_postgres_log_api`.

### Flush Modes:
| Mode | Description |
| :--- | :--- |
| `now` | Validate and insert records immediately into PostgreSQL (default). |
| `buffer` | Validate records and append to memory buffer. Returns immediate ack. |
| `flush` | Internal mode: bulk-inserts all pending records with a multi-row `INSERT`. |

Rows are taken out of the buffer before each insert, so concurrent requests never insert the same rows twice or lose rows added meanwhile. A failed insert puts its rows back at the front for the next flush.

### Periodic Background Flush Loop:
Atom runs a periodic background task (`func_postgres_buffer_flush_periodic_task`) draining both buffers every `config_postgres_buffer_flush_auto_sec` (default 60s). It acquires `runtime_lock_postgres_buffer_flush` to serialize flushes and ensure no lost writes.

---

## 5. API Logging & Telemetry (`log_api`)

Atom captures structured telemetry for every incoming request in the `log_api` table (failed writes are counted on the Monitor page's Background tab, `GET /admin/monitor?view=background`; rows wait in the buffer and are retried):

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
config_postgres_url_master=postgresql://atom:pass@primary-db:5432/atom
config_postgres_url_logs=postgresql://logger:pass@logs-db:5432/atom_logs
config_postgres_db_log_api=logs
```
Atom resolves `app.state.client_postgres_log_api = app.state.client_postgres_dict["logs"]` and routes log writes, cleanup and `/my/api-usage` to it. Schema init creates only the `log_api` table there and leaves other tables untouched; with schema init off, startup stops if `log_api` is missing.
