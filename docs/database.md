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

Routes Atom flags: the reads `/my/profile`, `/my/object-read`, `/my/object-read-export`, `/my/message-inbox`, `/my/message-thread`, `/private/object-read`, `/private/object-read-export`, `/private/user-read`, `/private/table-column-groupby`, `/private/table-column-distinct`, `/public/object-read`, `/public/object-read-export`, `/public/table-column-groupby`, `/public/table-column-distinct`, `/admin/object-read`, `/admin/object-read-export`, `/admin/table-column-groupby`, `/admin/table-column-distinct`, `/admin/postgres-schema`, `/admin/postgres-info`, `/admin/postgres-slow-queries`, `/admin/postgres-slow-queries-reset`, `/admin/postgres-query-runner-read`, `/admin/postgres-query-runner-read-export`, `/admin/postgres-query-ai`, `/admin/postgres-import`, and `/admin/monitor` (its Database tab); the writes `/admin/object-create`, `/admin/object-update` and `/admin/object-delete` (role 1). The list in `config_api` is the source of truth; a project flags its own routes the same way.

**Writes on another database.** Every generic write route (`object-create`, `object-update`, `object-delete` and `object-delete-all` under `/my`, `/permission` and `/admin`, and `/public/object-create`) checks its columns (`created_by_id`, `updated_by_id`, the ownership column) against the chosen database's schema and writes there; buffered rows (`mode=buffer`) are flushed to that database and queued jobs (`queue=`) carry its name to the consumer. Atom flags only the `/admin` writes; a project turns the others on by adding `"is_connection_param": True` to their entry in `config_extend.py`.

Two controls decide where a write can go, and no extra setting: the route's flag, and what the database user in `config_postgres_url_<name>` may do. Once a write route is flagged, its callers can write to every database whose user has write rights, so give each URL only the rights it needs: a read-only user for replicas and reporting databases, and leave `/public/object-create` unflagged. A write the database refuses (a read-only replica) is an error, never redirected to master. `/my/object-read` marks messages read on the database it read them from: read messages on master, not on a read-only replica.

The user routes (`user-*`), `/my/object-create-mongodb` and `/admin/postgres-query-runner-write` (which takes a `connection` body field) stay as they are. SQL Server and ClickHouse routes pick their server with a body field also named `connection` (see section 3).
```bash
curl "http://localhost:8000/public/object-read?table=products&connection=replica1"    # replica1
curl "http://localhost:8000/public/object-read?table=products"                        # master
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/admin/postgres-schema?connection=analytics"
```

**The schema per database.** `cache_postgres_schema_dict` holds every database's tables and columns (type, nullable, default, primary key, unique, indexes), read with `func_postgres_schema_read` at startup and again by `GET /admin/sync`. `GET /admin/postgres-schema` returns that cache for the chosen database (master, or `?connection=<name>`) without querying the database, as `{table: {column: {...}}}` with `datatype`, `is_nullable` (`"YES"` or `"NO"`, as in `information_schema`), `column_default`, `is_primary`, `is_unique`, `is_index`, `index_names` and `relation_type` per column, so it shows exactly the columns Atom checks requests against. A column added by hand in SQL appears there, and in the CRUD routes, after `/admin/sync` or a restart.

---

## 2. Declarative Schema Management

Each database has its own schema: `config_postgres_schema_<name>` is applied at startup to the database of `config_postgres_url_<name>`, master first. `config_postgres_schema_master` holds Atom's tables; a project adds one for another database in `config_extend.py`, and that database gets exactly what its schema lists (nothing of Atom's, no `users`). A schema naming a database without a URL stops startup.

When `config_is_postgres_schema_init = True`, Atom inspects and automatically migrates each database on startup:
- Creates the PostgreSQL extensions of its `extension` part.
- Creates missing tables declared in its `table` part, with their primary key: `id`, several columns (`device`, `time`), or none.
- Adds missing columns and alters types if necessary.
- Installs unique constraints, checks and indexes from the column specs.
- Where the `users` table is (master): seeds the root admin user (`admin` / `role: 1`) and attaches the root protection trigger.
- Runs its `sql` part last (for example `create_hypertable`, [timescaledb.md](timescaledb.md)).

```python
# config_extend.py: a second database, telematics (config_postgres_url_telematics in .env)
config_postgres_schema_telematics = {
"extension": ["timescaledb"],
"table": {"reading": [{"name": "device", "datatype": "text", "is_primary": True}, {"name": "time", "datatype": "timestamptz", "is_primary": True}, {"name": "speed", "datatype": "real"}]},
"sql": {"reading_hypertable": "SELECT create_hypertable('reading', 'time', if_not_exists => TRUE)"},
}
```

**`id` is optional.** A table with `id` (an integer) gets every generic route; on a table without it, create and read work (read with an `order`, e.g. `order=time desc`), while update, delete and relation fetch answer 400 `table '<name>' has no id: ... needs one`, before any SQL.

It reads the current tables, columns, indexes, constraints and triggers once (a few catalog queries for all tables), then changes only what differs from `config_postgres_schema_master`; an unchanged database takes about 14 queries, so a start against a remote database stays near one second. Tables, the root user and triggers change in one transaction: other sessions see the old schema or the new one, and a delete guard is never missing while an instance starts. A trigger is recreated only when its definition differs, so a guard removed or edited by hand is put back on the next start. Extensions run before that transaction (a missing privilege is skipped) and custom `sql` after it.

**Busy tables and big changes.** In that transaction each table lock is waited for at most `config_postgres_lock_timeout_sec` (10 s): when another session holds a table that long, startup stops with `schema init: a table stayed locked ... nothing was changed` instead of hanging the deploy, and the whole change rolls back. To see what the next start would change before deploying, run the plan with the new code against the target database:

```bash
venv/bin/python -m script.postgres_schema_plan
venv/bin/python -m script.postgres_schema_plan --db telematics    # one database only
```

It plans every database that has a schema and a URL. It reads the catalog on a read-only connection, changes nothing, and prints each change, flagging the ones that lock or rewrite a table (`ALTER COLUMN ... TYPE`, `SET NOT NULL`, `CREATE INDEX` without `CONCURRENTLY`, `DROP`) with the table's estimated rows. A flagged change on a big table is better run by hand when it is quiet; the next start then finds nothing to change. Statements that run on every start (trigger functions, the root user) are only counted.

`venv/bin/python -m script.postgres_schema_plan --apply` prints the same plan, then runs it exactly as startup does (one transaction, the same advisory lock and lock timeout). With `config_is_postgres_schema_init = False`, startup changes nothing and only compares: if a database differs from its `config_postgres_schema_<name>` it stops, listing the changes, so the app never runs against a schema its code does not expect. A production deploy then is: `postgres_schema_plan`, read it, `postgres_schema_plan --apply`, start the app.

---

## 3. Query Runner & AI SQL Engine (`/admin/postgres-query-runner-*`)

Administrators can execute raw SQL. Reads accept `?connection=<name>` to pick a database; writes always use master:
```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-read?connection=replica1" -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" -d '{"sql": "SELECT count(*) FROM users;"}'
```
MSSQL and ClickHouse have their own routes: `/admin/mssql-query-runner-*` and `/admin/clickhouse-query-runner-*`. They take body param `connection` (default `master`) to pick a server from `config_mssql_url_<name>` or `config_clickhouse_url_<name>`; an unknown name returns 404.

### Natural Language AI SQL Generation:
When an OpenAI, Gemini or Anthropic (Claude) key is configured, `POST /admin/postgres-query-ai` (`func_postgres_query_ai`) turns a question into one validated SELECT from the cached schema (`cache_postgres_schema`): body `question`, `ai` (`gemini`, `openai` or `claude`), `execute` (default `false`). Without `execute` it returns `{sql, message, warnings}` for review; with `execute: true` it also runs the SQL through the read runner above (read-only transaction, 30 s timeout, `config_query_runner_read_limit` rows) and adds `rows`. `?connection=replica1` runs it on a replica. `POST /admin/clickhouse-query-ai` is the same for ClickHouse (body `connection`, reads with `readonly=1`).

A read-only transaction blocks every data and schema change, but not every side effect a function can have (`pg_terminate_backend`, `dblink`, advisory locks). For a full guarantee, point the connection at a replica or a login with only `SELECT` grants.

---

## 4. In-Memory Write Buffering

Atom can buffer high-volume write requests in application memory and insert them in bulk batches. This drastically reduces database round-trips for non-urgent records.

### The Two Runtime Buffers:
Lifespan initializes two independent buffer dictionaries on `app.state`:
1. **`buffer_postgres_create`**: Holds records submitted via object-create APIs with `mode=buffer`, and by project code calling `func_postgres_create(mode="buffer")`.
2. **`buffer_postgres_log_api`**: Holds request audit records produced by the HTTP middleware, for the `config_postgres_db_log_api` database.

Each buffered row keeps its database: the buffer key is `<connection>|<table>|<columns>|<on_conflict>`, and a flush writes each database's rows through that database's pool (`client_postgres_dict[<connection>]`). A database whose pool is missing, or whose insert fails, keeps its rows for the next flush (counted under `buffer_flush` on the Monitor page's Background tab, which lists each buffer with its database); the other databases are still written.

### Writing to another database from project code
A route that takes rows from another system (a device webhook, a feed) calls `func_postgres_create` with that database's pool, schema and name:
```python
await app_state.func_postgres_create(client_postgres=app_state.client_postgres_dict["telemetry"], client_postgres_conn=None, client_password_hasher=None,
    cache_postgres_schema=app_state.cache_postgres_schema_dict["telemetry"], buffer_postgres=app_state.buffer_postgres_create,
    buffer_rows_max=app_state.config_buffer_rows_max, buffer_full_mode="reject", config_column_regex=app_state.config_column_regex,
    buffer_limit=app_state.func_buffer_limit(app_state=app_state, table="gps_point"), mode="buffer", table="gps_point", obj_list=points,
    connection="telemetry", on_conflict="nothing")
```
| Argument | Effect |
| :--- | :--- |
| `connection` | The database name the pool and schema belong to (default `master`); buffered rows are flushed there |
| `on_conflict="nothing"` | `ON CONFLICT DO NOTHING`: a row that hits a primary or unique key is skipped, so a sender's retry or an overlapping backfill never fails a batch |
| (automatic) | `RETURNING id` only when the table has an `id` column: a TimescaleDB hypertable keyed on device and time has none, and returns `"created"` |

### Flush Modes:
| Mode | Description |
| :--- | :--- |
| `now` | Validate and insert records immediately into PostgreSQL (default). |
| `buffer` | Validate records and append to memory buffer. Returns immediate ack. |
| `flush` | Internal mode: bulk-inserts all pending records with a multi-row `INSERT`. |

Rows are taken out of the buffer before each insert, so concurrent requests never insert the same rows twice or lose rows added meanwhile. A failed insert puts its rows back at the front for the next flush.

### Periodic Background Flush Loop:
Atom runs a periodic background task (`func_postgres_buffer_flush_periodic_task`) draining both buffers, each database every `config_postgres_buffer_flush_auto_sec_<name>` seconds when set, else every `config_postgres_buffer_flush_auto_sec` (default 60s): for example `config_postgres_buffer_flush_auto_sec_telemetry=2` writes device points every 2 seconds while master keeps its minute. A name without a `config_postgres_url_<name>` stops startup. Each flush acquires `runtime_lock_postgres_buffer_flush` to serialize flushes and ensure no lost writes. A buffer is also written when one key reaches its row limit (`config_buffer_limit_<table>`, else `config_buffer_limit_default`), on `GET /admin/sync` and once more at shutdown.

Buffered rows live in the process's memory: rows not yet flushed are lost if the process crashes. Keep the interval short for data a sender won't send again, and fill gaps from the sender's history API with `on_conflict="nothing"`.

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
Then move the `log_api` table into that database's schema, explicitly, in `config_extend.py`: out of master's schema, into the logs one (the same definition, not a copy):
```python
config_postgres_db_log_api = "logs"
config_postgres_schema_master = {**base_config_postgres_schema_master, "table": {k: v for k, v in base_config_postgres_schema_master["table"].items() if k != "log_api"}}
config_postgres_schema_logs = {"table": {"log_api": base_config_postgres_schema_master["table"]["log_api"]}}
```
Startup stops while API logging is on and `log_api` is not in the schema of `config_postgres_db_log_api`'s database, or is in another one too. Atom resolves `app.state.client_postgres_log_api = app.state.client_postgres_dict["logs"]` and routes log writes, cleanup and `/my/api-usage` to it.
