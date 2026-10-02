# 🛠️ Admin Toolkit & Built-in Web Interfaces

Atom includes high-privilege administrative utilities, schema inspection tools, data import runners, and embedded zero-dependency web interfaces.

---

## 1. Built-in Web Interfaces

Atom embeds two single-page browser interfaces in `static/`:

### A. API Master (`static/api.html`)
Served by default at `/` (`config_root_html_path = "static/api.html"`):
- **Live Endpoint Introspection**: Dynamically displays all endpoints, schemas, and parameter requirements.
- **Interactive Request Runner**: Test GET, POST, PUT, DELETE, and WebSocket connections with headers and request payloads.
- **cURL Importer**: Paste raw curl commands to auto-populate request inputs.
- **Multi-View Response Inspector**: Tree view, raw JSON, and tabular renderers.

### B. PgWeb (`static/pgweb.html`)
Lightweight browser-based PostgreSQL database manager:
- **Schema & Table Inspector**: View tables, columns, indexes, and constraints.
- **SQL Runner**: Execute queries directly from the browser with tabular result visualization.
- **Data Browser**: Browse, sort, and filter live table data.

---

## 2. Administrative APIs (`/admin/*`)

Access to `/admin/*` requires an authenticated user with **`role: 1`** (root superadmin).

### 1. Raw SQL Query Runner (`POST /admin/postgres-query-runner-read`)
Executes read SQL on master, or on another database with `?postgres=<name>`:
```bash
POST /admin/postgres-query-runner-read?postgres=replica1
{"sql": "SELECT count(*) FROM users;"}
```

### 2. Table Data Imports (`POST /admin/*-import`)
Bulk import data from external systems into PostgreSQL:
- **Postgres Import** (`/admin/postgres-import`): Import a CSV into a table (form fields `mode`, `table`, `file`; target database with `?postgres=<name>`, default master).
- **MongoDB Import** (`/admin/mongodb-import`): Ingest BSON collections into structured relational tables.

### 3. Schema and Cache Refresh
- **Schema** (`GET /admin/postgres-schema`): Reads the current PostgreSQL schema (master, or `?postgres=<name>`).
- **Refresh caches** (`GET /admin/sync`): Flushes the create buffer, then re-reads every schema cache, the OpenAPI spec, `cache_config` and the user role/status caches without a restart.

### 4. Runtime Status (`GET /admin/runtime-status`)
Shows failures that happen outside a request's response, which are otherwise only printed:
```json
{"error_count": {"log_api_write": 0, "buffer_flush": 0, "buffer_dropped": 0, "background_task": 0, "cleanup": 0},
 "buffer_rows_pending": {"create": 0, "log_api": 0},
 "background_tasks_running": 0}
```
- `log_api_write`: API log rows that could not be written (printed on the 1st failure and every 100th, so an outage does not flood the log).
- `buffer_flush`: failed buffer flushes. The rows stay in `buffer_rows_pending` and are retried on the next flush, so a growing number means the database has been unreachable for a while.
- `buffer_dropped`: API-log rows dropped because the log buffer reached `config_buffer_rows_max` during an outage (user-data buffers reject new rows with 503 instead).
- `background_task`: failed `?is_background=true` requests.
- `cleanup`: failed OTP, API-log or in-memory cache cleanups.

Counts are per process and reset on restart.
