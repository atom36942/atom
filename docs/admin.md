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
- **Sidebar**: Tables, Views and Materialized tabs show their counts; hover a name and click its copy icon to copy it without opening it.
- **Data Browser**: Browse, sort, and filter live table data, 100 rows per page by default (pick 50, 100 or 500; remembered). When a `LIKE`/`ILIKE` filter that starts with `%` takes 100 ms or more, a bar under the filter explains it is a full table scan and offers the trigram index SQL that makes such searches fast (`CREATE EXTENSION IF NOT EXISTS pg_trgm;` plus a `gin_trgm_ops` index on the column).
- **Row Panel**: Click any cell in the Rows tab: a panel beside the grid shows every column of that row, with long text wrapped (each long value scrolls on its own), JSON pretty-printed, and copy and expand icons per field (expand opens the value in a large, view-only window). Its header shows the table and the row's key (`users · id = 22`) and a field filter. Clicking another cell switches the panel to that row; clicking anywhere else (empty grid space, headers, toolbar, sidebar) closes it; the grid's scrollbars and column resize handles do not. Drag the panel's left edge to widen it for long values (remembered; double-click the edge to reset). Selecting text in the grid does not open it, and double-clicking a cell opens the large view directly. Values are edited only in the panel. ↑/↓ move to the previous or next row, Esc closes it. Each field's pencil edits it in place (same rules as cell editing below), and the trash icon deletes the row after a confirmation: the row is found by its primary key, deleting is refused in read-only mode, and refused if the row changed since it was shown.
- **Cell Editing**: In the row panel, click a field's pencil; **Save** (or ⌘/Ctrl+Enter) writes it, **Set NULL** clears a nullable column. The row is found by its primary key and the value is converted by PostgreSQL to the column's type, so a wrong format shows PostgreSQL's error and saves nothing. Editing is off in read-only mode and for views, tables without a single-column primary key, the key column, generated and identity columns, arrays and binary columns (use the SQL Runner for those). If the cell changed since the rows were loaded, the save is refused so nobody's change is overwritten; reload and try again.

PgWeb's own requests are not written to `log_api` (`"is_log_api": False` on `/pgweb` in `config_api`), so browsing does not fill the API log. PgWeb can run any SQL on any database it connects to, so `/pgweb` is off by default. Set `config_is_pgweb_enabled=true` in `.env` on a developer machine only. Even then it accepts a request only when:

- it comes directly from this machine (`127.0.0.1`/`::1`), with no proxy or tunnel headers such as `X-Forwarded-For`, so `ngrok`, `cloudflared`, nginx or a sidecar cannot expose it;
- its `Origin`, if any, is Atom's own address, so other websites open in your browser cannot send it SQL;
- it is sent as `Content-Type: application/json`, which browsers cannot send cross-site without a CORS preflight.

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

### 5. Slow Queries (`GET /admin/postgres-slow-queries`)
Lists this database's most expensive statements from `pg_stat_statements` (master, or `?postgres=<name>`). Values in the query text are already `$1`, `$2` placeholders.

- `limit`: rows to return, `1`–`100` (default `20`).
- `order`: `total_time` (default; where the database spends its time), `mean_time` (slowest single calls) or `calls`.
- Each row has `calls`, `total_ms`, `mean_ms`, `max_ms`, `rows`, cache `shared_blks_hit`/`shared_blks_read`, the `query` and `share_pct` of all statement time in this database. `since` is when the counters were last reset.
- When the extension is not enabled the response is `{"is_enabled": false, "help": ...}` instead of an error. See [performance.md](performance.md#3-slow-queries) to enable it.

`POST /admin/postgres-slow-queries-reset` clears the counters for the current database only, so you can measure a fresh period: reset, use the app or run the load test, then read the report.
