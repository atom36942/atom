# 🛠️ Admin Toolkit & Built-in Web Interfaces

Atom includes high-privilege administrative utilities, schema inspection tools, data import runners, and embedded zero-dependency web interfaces.

---

## 1. Built-in Web Interfaces

Atom embeds single-page browser interfaces in `static/`. The page at `/` (`config_root_html_path`) lists them all. They share one dark theme, and the ones that log in (API, Monitor, Admin, Message) are built on the same four blocks (look, account, account header, dialogs), copied unchanged between them: see [Page standard](page.md#page-standard). Logged in, the header shows **Sync** and an avatar with the username's initials, opening **My profile**, **Login details** (username, password with a pencil to change it, role) and **Logout**; the Sync dialog shows what the page keeps in the browser and downloads it again.

### Home (`/`)
Served at `/`: a table of every page, from `GET /static-pages` (public, kept out of `log_api`). A page is a top-level `.html` file or a folder with an `index.html`, opened by name at `GET /page/<name>` (`<name>.html` or `<name>/index.html` → `/page/<name>`; public, revalidated on every load), in Atom's `static/` and the project's `static_extend/`, the home page included, whatever the name; other files (CSV, scripts, images, folders without `index.html`, deeper pages) are skipped but still served at `/static/...`. Two pages with one name stop startup. Each `/static-pages` entry is `{name, url, folder, path}`; with `config_is_home_atom_listed=false` it lists only `static_extend/` pages, so the home page shows just the project's (Atom's still open at `/page/<name>`). Each row shows the page's name (its file or folder name with the first letter capitalized) and its path; clicking the row opens the page in a new tab. Search with `/`, Enter opens the first match.

### A. API (`/page/api`)
- **Live Endpoint Introspection**: Dynamically displays all endpoints, schemas, and parameter requirements.
- **Interactive Request Runner**: Test GET, POST, PUT, DELETE, and WebSocket connections with headers and request payloads.
- **cURL Importer**: Paste raw curl commands to auto-populate request inputs.
- **Multi-View Response Inspector**: Tree view, raw JSON, and tabular renderers.
- **Login**: the page works logged out (public routes). **Log in** opens the standard login dialog (any role); running any `/auth/login-*` route in the runner logs the page in too, and running `/my/token-refresh` keeps the new token. localStorage `api` = `{v, token, user, synced_at}`; the OpenAPI spec is the IndexedDB record `openapi`, downloaded on first open and by every sync, so the page opens without waiting; the responses stay in memory.

### B. PgWeb (`/page/pgweb`)
Lightweight browser-based PostgreSQL database manager:
- **Schema & Table Inspector**: View tables, columns, indexes, and constraints.
- **SQL Runner**: Execute queries directly from the browser with tabular result visualization.
- **Sidebar**: Tables, Views and Materialized tabs show their counts; hover a name and click its copy icon to copy it without opening it.
- **Data Browser**: Browse, sort, and filter live table data, 100 rows per page by default (pick 50, 100 or 500; remembered). Pages follow the primary key with the server's cursor (`after`, as in [Paging](crud.md#paging)): Next and Previous only, the same speed on any page; a table without a single-column primary key shows its first page only. When a `LIKE`/`ILIKE` filter that starts with `%` takes 100 ms or more, a bar under the filter explains it is a full table scan and offers the trigram index SQL that makes such searches fast (`CREATE EXTENSION IF NOT EXISTS pg_trgm;` plus a `gin_trgm_ops` index on the column).
- **Row Panel**: Click any cell in the Rows tab: a panel beside the grid shows every column of that row, with long text wrapped (each long value scrolls on its own), JSON pretty-printed, and copy and expand icons per field (expand opens the value in a large, view-only window). Its header shows the table and the row's key (`users · id = 22`) and a field filter. Clicking another cell switches the panel to that row; clicking anywhere else (empty grid space, headers, toolbar, sidebar) closes it; the grid's scrollbars and column resize handles do not. Drag the panel's left edge to widen it for long values (remembered; double-click the edge to reset). Selecting text in the grid does not open it, and double-clicking a cell opens the large view directly. Values are edited only in the panel. ↑/↓ move to the previous or next row, Esc closes it. Each field's pencil edits it in place (same rules as cell editing below), and the trash icon deletes the row after a confirmation: the row is found by its primary key, deleting is refused in read-only mode, and refused if the row changed since it was shown.
- **Cell Editing**: In the row panel, click a field's pencil; **Save** (or ⌘/Ctrl+Enter) writes it, **Set NULL** clears a nullable column. The row is found by its primary key and the value is converted by PostgreSQL to the column's type, so a wrong format shows PostgreSQL's error and saves nothing. Editing is off in read-only mode and for views, tables without a single-column primary key, the key column, generated and identity columns, arrays and binary columns (use the SQL Runner for those). If the cell changed since the rows were loaded, the save is refused so nobody's change is overwritten; reload and try again.

PgWeb's own requests are not written to `log_api` (`"is_log_api": False` on `/pgweb` in `config_api`), so browsing does not fill the API log. PgWeb can run any SQL on any database it connects to, so `/pgweb` is off by default. Set `config_is_pgweb_enabled=true` in `.env` on a developer machine only. Even then it accepts a request only when:

- it comes directly from this machine (`127.0.0.1`/`::1`), with no proxy or tunnel headers such as `X-Forwarded-For`, so `ngrok`, `cloudflared`, nginx or a sidecar cannot expose it;
- its `Origin`, if any, is Atom's own address, so other websites open in your browser cannot send it SQL;
- it is sent as `Content-Type: application/json`, which browsers cannot send cross-site without a CORS preflight.

---

### C. Monitor (`/page/monitor`)
One page for how the server is doing, with a tab per topic; each fact appears on one tab only, and a line under the tabs says what the tab covers and whether it is this worker or the whole server; every card has one line under its title saying what it shows and what to look for, and every number tile an ⓘ that explains it on hover or tap. Each tab loads its data when opened, and Refresh reloads it; the page remembers the last tab and choices.
- **Memory**: the RAM of the worker that answers: process and machine memory, uptime, threads and CPU time; RAM over time (read once a minute since the worker started, up to the last 24 hours, one `psutil` call; kept in the worker's memory, so a restart starts it again; a leak shows as a line that keeps rising); each item Atom keeps on `app_state` with its kind from the name prefix (`cache` safe to lose, `buffer` rows waiting to be written, `runtime` live state, `config`, `extend`; `other` means a name without a known prefix), entries and size, biggest first (sizes and counts only, never values; clients are left out, see App); the total of Python objects (a number that keeps rising between refreshes points to a leak) and the most common object types, to spot leaks; and allocation tracing: Start turns on Python's `tracemalloc` and lists the source lines holding the most memory, each marked Atom, Project or Package. It slows the worker, so it stops by itself after 5 minutes.
- **Requests**: traffic from `log_api` for the last hour, 24 hours or 7 days: totals, error rate, average and p95 response time, a requests-over-time chart, the busiest and slowest APIs, status codes and the most active users.
- **Errors**: failed requests (status 400 and above) split into server (500+) and client (400–499) errors, grouped by API and status with the last error, and the latest 50 failures. Background failures are on Background.
- **Database**: which connection it reads (always shown as a picker) and where it points (database, host, port, user, version); pool use for every PostgreSQL connection, marking the one `log_api` writes to; and for the chosen one: size, connections, cache hit ratio, waiting locks, queries running over 5 seconds, the biggest tables (rows, dead rows, scans, last vacuum) and the most expensive statements (needs `pg_stat_statements`).
- **Background**: periodic tasks (RAM history among them), rows waiting in the write buffers, running background tasks, open websockets, and error counters. Failed queue jobs are kept in each broker's `<channel>_failed` (see the queue docs); for the queue Redis, the page shows each channel's waiting, running and failed jobs and whether a consumer holds it.
- **App**: Atom's version, Python, packages, workers, mode, routes and `func_*` functions (each split into Atom's and the project's), which clients are on, and every `config_*` setting; secrets and connection URLs only show whether they are set.

With `config_uvicorn_workers` above 1, Memory and Background describe the worker that answers, and each refresh may reach a different one; the header names it. Requests and Errors need API logging (`log_api`).

The page is independent of the other pages: it logs in itself (role 1, the page standard) and keeps one localStorage key, `monitor` = `{v, token, user, synced_at, tab, hours, connection}`, so it works on a server without the API console. Its Sync downloads the user again. It reads `GET /admin/monitor` (see 4b). Current RAM uses the `psutil` package.

### D. Admin (`/page/admin`)
A panel for the backend's super admin (role 1 only), built on the `/admin/*` routes and nothing else.
- **Login**: the standard login dialog with role 1 fixed (a deactivated or deleted admin is logged out). The header has **Refresh** (reads the current view again) and **Sync** (the user and the reference data below). Confirmations and forms use the shared dialog.
- **Browser storage** (the page standard): localStorage `admin` = `{v, token, user, synced_at, range, limit, columns, groupby}`; IndexedDB `admin`, one record `reference` holding the schema, `/info`, row counts, server settings, triggers and CHECK constraints. On open the page draws from that record; the first login (or a cleared browser) downloads it first, and every sync (3 hours, or Sync now) downloads it again. Rows and dashboard numbers always come from the server. Logout removes the key and the database, in every open tab.
- **Rules from the server**: at start (and on Refresh) the page reads the running server's settings from `GET /admin/monitor?view=app` (`config_column_users_blocked`, `config_column_single_update`, `config_column_read_blocked`, `config_is_user_delete`, `config_is_read_only`, `config_is_log_api`, `config_postgres_db_log_api`, `config_batch_item_limit`; Atom's defaults when it can't) and the triggers `config_postgres` control installs (`pg_trigger`: `trigger_delete_disable_<table>`, `..._bulk_`, `..._is_protected_`, `trigger_updated_at_set_<table>`, ...), so it follows the project's own config. On a read-only server (`config_is_read_only`) a banner says so and every change is off.
- **Sidebar**: Dashboard, then every relation of the master database's public schema from `GET /admin/postgres-schema`, grouped by what PostgreSQL says it is (Tables, Views, ...), each table with its row estimate (`pg_stat_user_tables`) and `read-only` on the tables Atom writes. Type to find one, Enter opens it.
- **Explicit values**: everything shows as stored: `null`, `""` for an empty string, times as `2026-11-09 01:46 +05:30` (this browser's time zone, with the stored value beside it in the record panel), codes as `1 (File)` from `config_column_int_mapping`, roles as `1 (admin)`, user ids as `812 (riya@example.com)`. Filter chips read as the condition they send (`title ilike %rep%`, `email is null`); the computed `state` column says it comes from `deactivated_at` and `deleted_at`; dashboard tables name the columns they count. The address keeps the view (`#dashboard`, `#table/<name>`).
- **Server caches**: the page uses what the server already has cached (schema, config, user roles and statuses) and never reloads them; a change Atom caches (a `config` row; a user's role, permissions, `deactivated_at` or `deleted_at`) takes effect when the server reloads its caches (`GET /admin/sync`) or restarts.
- **Dashboard** (last 24 hours, 7 days or 30 days; counts per role, status code and user from `GET /admin/table-column-groupby`, totals and charts from `POST /admin/postgres-query-runner-read`; `log_api` is read from the database it is written to, `config_postgres_db_log_api`): users (total, active, deactivated, deleted, new, active in the range), requests, error rate and response time from `log_api`, database size; users by role (click a role to list its users); new users and API requests over time; busiest APIs, status codes, most active users, tables by size, and the latest errors. Monitor has the deeper server view.
- **Table**: rows from `GET /admin/object-read`, newest first, paged after the server's cursor (`after`) in any sort, Next and Previous only. Search looks in every text column (and the id); filters are column, operator (contains, =, ≠, ≥, ≤, is empty, is set) and value, shown as removable chips; click a header to sort; Group by counts the rows per value of a column within the current filters (`GET /admin/table-column-groupby`, top 50) and a click on a value filters the list to it; Columns picks what shows (remembered per table); Export CSV uses `GET /admin/object-read-export` with the same filters and order; **curl** copies the list request (table, filters, order, page size) as a curl command with a `$TOKEN` placeholder. Column headers show the type, keys (primary, unique, index), default and who sets the column. A note under the toolbar says what the table does not allow and which rule stops it.
- **Schema tab**: each column with its type, keys and who sets it (server, a state button, the form, or blocked by a `config_column_*` rule), the rules for new rows, edits and deletes here, the routes behind them, the indexes and the triggers with what each does. Tables with `deactivated_at` or `deleted_at` get a `state` column (active, deactivated, deleted). Ids that point at users (`*_by_id`, `user_id`, ...) show the id and the username, and open that user.
- **Record panel**: click a row to see every field (JSON pretty-printed, times in local time, key badges per column) with the audit columns last; ↑/↓ move to the previous or next row. State buttons set or clear a timestamp: Deactivate/Reactivate (`deactivated_at`), Soft delete/Restore (`deleted_at`), Mark verified/Unverify (`verified_at`), Mark read/unread (`read_at`), with the matching `*_by_id` set to the admin. Copy JSON copies the row. Leaving an edit with unsaved changes (Escape, ×, another row or table) asks first. Delete asks first; when a rule forbids it the button is off and says why. Tick rows to run the same state buttons or Delete on many at once, sent in batches of `config_batch_item_limit`.
- **CHECK constraints**: Atom writes `config_postgres` `in`, `regex` and `check` as CHECK constraints, so the page reads them from `pg_constraint` (one query) and shows them as badges and under each input: an `in` list becomes a select, a regex is checked before saving (with `config_column_regex` for username and password), any other condition is written out. The Schema tab lists every constraint of the table.
- **Forms follow Atom's rules**: `id`, `created_at`, `created_by_id`, `updated_at` and `updated_by_id` never show (the server sets them); state columns and their `*_by_id` change only through their buttons; read-blocked columns (`password`) never show; geography columns are left to the SQL runner. A NOT NULL column without a default is required on create and can't be emptied on edit; a default shows as the placeholder. Empty means NULL.
- **Users** go through the user routes: New user (`/admin/user-create`: role, username, password), Edit, the state buttons and Reset password (`/admin/user-update`; username, email and mobile are sent one at a time), Delete (`/admin/user-delete`, refused unless `config_is_user_delete`). The root user (id 1) cannot be deactivated or deleted, and `deleted_at` is not set from here (`config_column_users_blocked`).
- **Other tables** use `/admin/object-create`, `/admin/object-update` and `/admin/object-delete`; a table without `created_by_id` or `updated_by_id` cannot be added to or edited here (those routes need them), and views are read-only. Tables Atom writes itself (`log_api`, `otp`, `log_users_password`, `log_users_delete`, `blob`) are read-only here. Delete is off on tables with a delete guard (`table_row_delete_disable`, e.g. `config`, whose rows are deactivated instead) and for rows with `is_protected` where `is_protected_delete_disabled` is on.

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
- **Postgres Import** (`/admin/postgres-import`): Import a CSV into any table, `users` included (form fields `mode` = `create`/`update`/`delete`, `table`, `file`; target database with `?connection=<name>`, default master). A `password` column in `users` is hashed (Argon2) on create and update.
- **MongoDB Import** (`/admin/mongodb-import`): Ingest BSON collections into structured relational tables.

### 3. Schema and Cache Refresh
- **Schema** (`GET /admin/postgres-schema`): Returns Atom's schema cache (`cache_postgres_schema_dict`) for master, or for another database with `?connection=<name>`, with no database query: tables, and per column the type, nullable, default, primary key, unique and indexes. It is what Atom checks requests against, refreshed at startup and by `/admin/sync` (see [Picking a database per request](database.md#picking-a-database-per-request-connectionname)). Any other query parameter is refused.
- **Refresh caches** (`GET /admin/sync`): Flushes the create buffer, then re-reads every schema cache, the OpenAPI spec, `cache_config` and the user role/status caches without a restart.

### 4. Background error counters
Failures that happen outside a request's response are otherwise only printed; the Monitor page's Background tab (`GET /admin/monitor?view=background`) counts them, next to the rows waiting in each write buffer:
- `log_api_write`: API log rows that could not be written (printed on the 1st failure and every 100th, so an outage does not flood the log).
- `buffer_flush`: failed buffer flushes. The rows stay in their buffer and are retried on the next flush, so a growing number means the database has been unreachable for a while.
- `buffer_dropped`: API-log rows dropped because the log buffer reached `config_buffer_rows_max` during an outage (user-data buffers reject new rows with 503 instead).
- `background_task`: failed `?is_background=true` requests.
- `cleanup`: failed in-memory cache cleanups.
- `schedule`: failed checks or starts of scheduled scripts (a script's own failure is its `script_run` row, [schedule.md](schedule.md)).

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
