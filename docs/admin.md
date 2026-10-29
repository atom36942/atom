# 🛠️ Admin Toolkit & Built-in Web Interfaces

Atom includes high-privilege administrative utilities, schema inspection tools, data import runners, and embedded zero-dependency web interfaces.

---

## 1. Built-in Web Interfaces

Atom embeds single-page browser interfaces in `static/`. The page at `/` (`config_root_html_path`) lists them all.

### Home (`/`)
Served at `/`: a table of every page, from `GET /static-pages` (public, kept out of `log_api`). A page is a top-level `.html` file or a folder with an `index.html`, opened by name at `GET /page/<name>` (`<name>.html` or `<name>/index.html` → `/page/<name>`; public, revalidated on every load), in Atom's `static/` and the project's `static_extend/`, the home page included, whatever the name; other files (CSV, scripts, images, folders without `index.html`, deeper pages) are skipped but still served at `/static/...`. Two pages with one name stop startup. Each `/static-pages` entry is `{name, url, folder, path}`; with `config_is_home_atom_listed=false` it lists only `static_extend/` pages, so the home page shows just the project's (Atom's still open at `/page/<name>`). Each row shows the page's name (its file or folder name with the first letter capitalized) and its path; clicking the row opens the page in a new tab. Search with `/`, Enter opens the first match. Light theme by default; the button beside the search switches to dark, remembered in this browser (`home` key).

### A. API (`/page/api`)
- **Live Endpoint Introspection**: Dynamically displays all endpoints, schemas, and parameter requirements.
- **Interactive Request Runner**: Test GET, POST, PUT, DELETE, and WebSocket connections with headers and request payloads.
- **cURL Importer**: Paste raw curl commands to auto-populate request inputs.
- **Multi-View Response Inspector**: Tree view, raw JSON, and tabular renderers.
- **Account Menu**: Logged out, the header shows **Login** (opens the login API). After logging in, the page saves the token and then the user from `GET /my/profile` under its `api` key, and shows an avatar with the user's first letter; clicking it lists who is logged in (username, role) and when the access token and the refresh token expire, with **Log out**. The saved user is read again from `/my/profile` when it is over 3 hours old.
- **Login Renewal**: The saved login stays alive on its own. On open, when the tab comes back into view, every minute and before each request, the page reads the access token's expiry from the token itself; with under 5 minutes left it gets new tokens from the refresh token (`POST /my/token-refresh`). When the refresh token has expired or is refused, the page logs out (as if never logged in) and says to log in again. A network failure keeps the token and retries at the next check. Running `/my/token-refresh` in the runner also saves the new tokens.

### B. PgWeb (`/page/pgweb`)
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

### C. Monitor (`/page/monitor`)
One page for how the server is doing, with a tab per topic; each fact appears on one tab only, and a line under the tabs says what the tab covers and whether it is this worker or the whole server. Each tab loads its data when opened, and Refresh reloads it; the page remembers the last tab and choices.
- **Memory**: the RAM of the worker that answers: process and machine memory, uptime, threads and CPU time; each item Atom keeps on `app_state` with its kind from the name prefix (`cache` safe to lose, `buffer` rows waiting to be written, `runtime` live state, `config`, `extend`; `other` means a name without a known prefix), entries and size, biggest first (sizes and counts only, never values; clients are left out, see App); the most common Python object types and garbage-collector stats, to spot leaks; and allocation tracing: Start turns on Python's `tracemalloc` and lists the source lines holding the most memory. It slows the worker, so it stops by itself after 5 minutes.
- **Requests**: traffic from `log_api` for the last hour, 24 hours or 7 days: totals, error rate, average and p95 response time, a requests-over-time chart, the busiest and slowest APIs, status codes and the most active users.
- **Errors**: failed requests (status 400 and above) split into server (500+) and client (400–499) errors, grouped by API and status with the last error, and the latest 50 failures. Background failures are on Background.
- **Database**: which connection it reads (always shown as a picker) and where it points (database, host, port, user, version); pool use for every PostgreSQL connection, marking the one `log_api` writes to; and for the chosen one: size, connections, cache hit ratio, waiting locks, queries running over 5 seconds, the biggest tables (rows, dead rows, scans, last vacuum) and the most expensive statements (needs `pg_stat_statements`).
- **Background**: periodic tasks, rows waiting in the write buffers, running background tasks, open websockets, error counters, and failed queue jobs from `tmp/consumer_failed_payload.jsonl` (without payloads).
- **App**: Python, packages, workers, mode, routes, which clients are on, and every `config_*` setting; secrets and connection URLs only show whether they are set.

With `config_uvicorn_workers` above 1, Memory and Background describe the worker that answers, and each refresh may reach a different one; the header names it. Requests and Errors need API logging (`log_api`).

The page is independent of the other pages: it logs in itself (username and password, role 1 only), keeps the login alive and shows the same account avatar menu as the API page, and keeps its token, user (`/my/profile`, read again after 3 hours) and choices under its own `monitor` key in the browser, so it works on a server without the API console. It reads `GET /admin/monitor` (see 4b). Current RAM uses the `psutil` package.

## 2. Administrative APIs (`/admin/*`)

Access to `/admin/*` requires an authenticated user with **`role: 1`** (root superadmin).

### 1. Raw SQL Query Runner (`POST /admin/postgres-query-runner-read`)
Executes read SQL on master, or on another database with `?connection=<name>`:
```bash
POST /admin/postgres-query-runner-read?connection=replica1
{"sql": "SELECT count(*) FROM users;"}
```

### 2. Table Data Imports (`POST /admin/*-import`)
Bulk import data from external systems into PostgreSQL:
- **Postgres Import** (`/admin/postgres-import`): Import a CSV into a table (form fields `mode`, `table`, `file`; target database with `?connection=<name>`, default master).
- **MongoDB Import** (`/admin/mongodb-import`): Ingest BSON collections into structured relational tables.

### 3. Schema and Cache Refresh
- **Schema** (`GET /admin/postgres-schema`): Reads the current PostgreSQL schema (master, or `?connection=<name>`).
- **Refresh caches** (`GET /admin/sync`): Flushes the create buffer, then re-reads every schema cache, the OpenAPI spec, `cache_config` and the user role/status caches without a restart.

### 4. Background error counters
Failures that happen outside a request's response are otherwise only printed; the Monitor page's Background tab (`GET /admin/monitor?view=background`) counts them, next to the rows waiting in each write buffer:
- `log_api_write`: API log rows that could not be written (printed on the 1st failure and every 100th, so an outage does not flood the log).
- `buffer_flush`: failed buffer flushes. The rows stay in their buffer and are retried on the next flush, so a growing number means the database has been unreachable for a while.
- `buffer_dropped`: API-log rows dropped because the log buffer reached `config_buffer_rows_max` during an outage (user-data buffers reject new rows with 503 instead).
- `background_task`: failed `?is_background=true` requests.
- `cleanup`: failed OTP, API-log or in-memory cache cleanups.

Counts are per process and reset on restart.

### 4b. Monitor (`GET /admin/monitor`)
The one route behind the Monitor page (admin only, kept out of `log_api`); helpers are in `function/monitor.py` and `function/memory.py`.
- `view`: `memory` (default), `requests`, `errors`, `database`, `background` or `app`.
- `hours`: `1`, `24` (default) or `168`, for `requests` and `errors`.
- `connection`: the PostgreSQL connection for `database` (default `master`).
- `trace`: `start` or `stop` turns allocation tracing on (for 5 minutes) or off first; use it with `view=memory`.

### 5. Slow Queries (`GET /admin/postgres-slow-queries`)
Lists this database's most expensive statements from `pg_stat_statements` (master, or `?connection=<name>`). Values in the query text are already `$1`, `$2` placeholders.

- `limit`: rows to return, `1`–`100` (default `20`).
- `order`: `total_time` (default; where the database spends its time), `mean_time` (slowest single calls) or `calls`.
- Each row has `calls`, `total_ms`, `mean_ms`, `max_ms`, `rows`, cache `shared_blks_hit`/`shared_blks_read`, the `query` and `share_pct` of all statement time in this database. `since` is when the counters were last reset.
- When the extension is not enabled the response is `{"is_enabled": false, "help": ...}` instead of an error. See [performance.md](performance.md#3-slow-queries) to enable it.

`POST /admin/postgres-slow-queries-reset` clears the counters for the current database only, so you can measure a fresh period: reset, use the app or run the load test, then read the report.
