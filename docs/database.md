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
config_postgres_pool_min_size=1
config_postgres_pool_max_size=10
config_postgres_pool_max_size_analytics=3    # optional, per database: analytics gets at most 3, the others 10
```
`config_postgres_pool_min_size_<name>` / `config_postgres_pool_max_size_<name>` size one database's pool; a database without them uses the shared two. The same works for SQL Server (`config_mssql_pool_min_size_<name>`, `config_mssql_pool_max_size_<name>`). A size for a name that has no URL (a typo such as `_tset`), or a max below its min, stops startup.
`config_postgres_query_timeout_sec` (default `0`, no limit) cancels any query on the app's pools that runs longer, so a hung query cannot hold a pool connection for good; it applies to startup's schema changes and exports too. If startup fails while opening the pools, the ones already open are closed.
Each name becomes a pool in `app.state.client_postgres_dict` (for example `client_postgres_dict["master"]`) with its schema in `app.state.cache_postgres_schema_dict`. Code that always uses the main database reads `client_postgres_dict["master"]`. Every URL needs a name: an unsuffixed `config_postgres_url` (also `config_redis_url`, `config_clickhouse_url`, `config_mssql_url`) or an empty `config_postgres_url_` stops startup.

### Picking a database per request (`?connection=<name>`)
`connection` is the one query parameter that picks which PostgreSQL database a request uses. Its value is a `<name>` from a `config_postgres_url_<name>` line in `.env` (`master`, `replica1`, `analytics`, ...).

| Situation | What happens |
| :--- | :--- |
| `connection` left out | The request uses `master` (the default) |
| `connection=<name>` on a route flagged `"is_connection_param": True` in `config_api` | The middleware (`func_middleware_postgres_select`) sets `request.state.client_postgres` to that database's pool and `request.state.cache_postgres_schema` to its schema from `cache_postgres_schema_dict[<name>]`; the route reads, filters and checks columns against that database |
| `connection=<name>` where `<name>` has no `config_postgres_url_<name>` | 404 |
| `connection=...` on a route without the flag | 400 `connection not allowed on this route`; the route always uses master |

Routes Atom flags (all reads): `/my/profile`, `/my/object-read`, `/my/object-read-export`, `/my/message-inbox`, `/my/message-thread`, `/private/object-read`, `/private/object-read-export`, `/private/users-list`, `/private/table-column-groupby`, `/private/table-column-distinct`, `/public/object-read`, `/public/object-read-export`, `/public/table-column-groupby`, `/public/table-column-distinct`, `/admin/object-read`, `/admin/object-read-export`, `/admin/table-column-groupby`, `/admin/table-column-distinct`, `/admin/postgres-schema`, `/admin/postgres-info`, `/admin/postgres-slow-queries`, `/admin/postgres-slow-queries-reset`, `/admin/postgres-query-runner-read`, `/admin/postgres-query-runner-read-export`, `/admin/postgres-query-generator-ai`, `/admin/postgres-import` and `/admin/monitor` (its Database tab). The list in `config_api` is the source of truth; a project flags its own routes the same way.

Writes (`object-create`, `object-update`, `object-delete`, the `user-*` routes, `/admin/postgres-query-runner-write`) are not flagged, so they always go to master. SQL Server and ClickHouse routes pick their server with a body field also named `connection` (see section 3).
```bash
curl "http://localhost:8000/public/object-read?table=products&connection=replica1"    # replica1
curl "http://localhost:8000/public/object-read?table=products"                        # master
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/admin/postgres-schema?connection=analytics"
```

**The schema per database.** `cache_postgres_schema_dict` holds every database's tables and columns (type, nullable, default, primary key, unique, indexes), read with `func_postgres_schema_read` at startup and again by `GET /admin/sync`. `GET /admin/postgres-schema` returns that cache for the chosen database (master, or `?connection=<name>`) without querying the database, as `{table: {column: {...}}}` with `datatype`, `is_nullable` (`"YES"` or `"NO"`, as in `information_schema`), `column_default`, `is_primary`, `is_unique`, `is_index`, `index_names` and `relation_type` per column, so it shows exactly the columns Atom checks requests against. A column added by hand in SQL appears there, and in the CRUD routes, after `/admin/sync` or a restart.

---

## 2. Declarative Schema Management

When `config_is_postgres_schema_init = True`, Atom inspects and automatically migrates the database schema on startup:
- Creates required PostgreSQL extensions (e.g. `uuid-ossp`, `citext`).
- Creates missing tables declared in `config_postgres["table"]`.
- Adds missing columns and alters types if necessary.
- Installs unique constraints and indexes from `config_postgres["index"]`.
- Seeds the root admin user (`admin` / `role: 1`) and attaches the root protection trigger.

It reads the current tables, columns, indexes, constraints and triggers once (a few catalog queries for all tables), then changes only what differs from `config_postgres`; an unchanged database takes about 14 queries, so a start against a remote database stays near one second. Tables, the root user and triggers change in one transaction: other sessions see the old schema or the new one, and a delete guard is never missing while an instance starts. A trigger is recreated only when its definition differs, so a guard removed or edited by hand is put back on the next start. Extensions run before that transaction (a missing privilege is skipped) and custom `sql` after it.

**Busy tables and big changes.** In that transaction each table lock is waited for at most `config_postgres_schema_lock_timeout_sec` (10 s): when another session holds a table that long, startup stops with `schema init: a table stayed locked ... nothing was changed` instead of hanging the deploy, and the whole change rolls back. To see what the next start would change before deploying, run the plan with the new code against the target database:

```bash
venv/bin/python -m script.schema_plan
```

It reads the catalog on a read-only connection, changes nothing, and prints each change, flagging the ones that lock or rewrite a table (`ALTER COLUMN ... TYPE`, `SET NOT NULL`, `CREATE INDEX` without `CONCURRENTLY`, `DROP`) with the table's estimated rows. A flagged change on a big table is better run by hand when it is quiet; the next start then finds nothing to change. Statements that run on every start (trigger functions, the root user) are only counted.

`venv/bin/python -m script.schema_plan --apply` prints the same plan, then runs it exactly as startup does (one transaction, the same advisory lock and lock timeout). With `config_is_postgres_schema_init = False`, startup changes nothing and only compares: if the master database differs from `config_postgres` it stops, listing the changes, so the app never runs against a schema its code does not expect. A production deploy then is: `schema_plan`, read it, `schema_plan --apply`, start the app. Only the master database is compared; a separate `log_api` database is not, but startup already stops if it has no `log_api` table.

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

Atom writes one row to the `log_api` table for every request to a `config_api` route (failed writes are counted on the Monitor page's Background tab, `GET /admin/monitor?view=background`; rows wait in the buffer and are retried). Routes with `"is_log_api": False` and paths that are not routes (static files, `/favicon.ico`, 404s) are left out; `config_is_log_api_all` logs those too.

### Columns:
- `created_at`, `created_by_id` (the user, or null), `ip_address`, `method`, `path`, `request_id` (sent back as `x-request-id`).
- `query_param`: the query string, secret and opaque values masked.
- `status_code`, `response_time_ms`, `response_type` (`cache_response`, `direct_no_cache_set`, `direct_cache_set`, `background_added`, `error`), `error`.
- `request_header`, `response_header`, `request_body`, `response_body`: filled only with `config_is_log_api_detail` (text bodies only: JSON, XML, plain text, `multipart/mixed`; up to `config_log_api_detail_max_kb`; secret headers masked, bodies only with `config_is_log_api_detail_mask`; see [config.md](config.md)).

### Storing Logs in an Isolated Database:
To keep high-volume log writes from contending with business transactions, route API logs to a dedicated PostgreSQL database:
```bash
# .env
config_postgres_url_master=postgresql://atom:pass@primary-db:5432/atom
config_postgres_url_logs=postgresql://logger:pass@logs-db:5432/atom_logs
config_postgres_db_log_api=logs
```
Atom resolves `app.state.client_postgres_log_api = app.state.client_postgres_dict["logs"]` and routes log writes, cleanup and `/my/api-usage` to it. Schema init creates only the `log_api` table there and leaves other tables untouched; with schema init off, startup stops if `log_api` is missing.
