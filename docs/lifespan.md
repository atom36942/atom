# 🔄 Application Lifespan

Atom wires up all its state in a single FastAPI **lifespan** context manager (`func_lifespan` in [`main.py`](../main.py)). It runs once on **startup** (everything before `yield`) and once on **shutdown** (everything after). This page walks through each phase, grouped by concern.

```
STARTUP  → validate → prepare dirs → init clients → init DB schema
         → build caches → register on app.state → generate OpenAPI → start flush loop
  yield  (app serves requests)
SHUTDOWN → stop background tasks → final buffer flush → close every client
```

If any startup step raises, the error is logged and re-raised so the app **fails fast** instead of booting half-initialized.

---

## Startup

### 1. Validation (`func_check`)
Before touching any resource, `func_check` validates that `config_api` is well-formed: every entry uses only allowed keys (`id`, `is_token_check`, `user_check_*`, `api_cache_sec`, `api_ratelimiting_times_sec`), flags are `0/1`, check `mode`s are valid (`redis` / `realtime` / `inmemory` / `token`), and ids/routes are consistent. A misconfigured API table stops the boot here.

### 2. Filesystem prep
Resets the working `tmp/` directory (removed if stale, then recreated) and ensures `secret/` exists — scratch space for uploads/temp artifacts and secret material.

### 3. Client initialization
Creates one client per configured integration. **Each is conditional** — if the relevant `config_*` value is unset, the client is `None` and that feature stays dormant. Highlights:

- **Password hasher & HTTP** — Argon2 `PasswordHasher` and a shared `httpx.AsyncClient` are always created.
- **Postgres** — `client_postgres` is the primary pool used for writes and default reads. Every `config_postgres_url_<name>` entry creates an additional pool in `client_postgres_dict`; supported read APIs can select one with `?db=<name>`.
- **Redis** — cache/rate-limit client and a separate queue-producer client.
- **Other datastores** — MongoDB (Motor), MSSQL write/read pools (with fallback).
- **Cloud/storage** — AWS S3 (async client + boto3 resource), SNS, SES; Azure Blob and Email.
- **AI** — OpenAI and Gemini clients.
- **Messaging** — Kafka producer (started here), RabbitMQ connection + channel, Celery producer.
- **Ops** — PostHog analytics, SFTP connection.

Every Postgres pool uses `config_postgres_pool_min_size` and `config_postgres_pool_max_size` (defaults `5` and `20`); MSSQL uses `pool_recycle=60`. Account for every app instance and every named Postgres pool when sizing database connection limits.

### 4. Database schema init
When `config_is_enable_postgres_schema_init = 1` and Postgres is present, `func_postgres_schema_init` applies the declarative schema from `config_postgres` — creating extensions, tables, columns, indexes, and constraints, and seeding the root admin user (password hashed with Argon2). See [config.md](config.md#config_postgres) for what it reads.

### 5. Cache building
To keep the request path fast, several read-mostly datasets are loaded into memory once at startup:

- **Schema caches** — `cache_postgres_schema` (+ an AI-oriented variant), plus derived `..._table_list` and `..._column_list`. These let routers validate table/column names without hitting the DB. `cache_postgres_db_name_list` contains the initialized named-pool keys used to validate the `db` query parameter.
- **Data caches** — `cache_config` (the `config` table), and `cache_users_role` / `cache_users_deactivated` / `cache_users_deleted`, which back the middleware's `inmemory`-mode auth checks.
- **Empty runtime caches** — `cache_ratelimiter`, `cache_api_response`, `cache_postgres_buffer_create` (the general write buffer), and `cache_postgres_buffer_log_api` (the dedicated API-log buffer) start empty and fill during operation.

### 6. Register on `app.state`
Every local variable named `client_*` or `cache_*` is bulk-assigned onto `app.state`, making all clients and caches reachable from routers as `request.app.state.<name>`. A `postgres_buffer_flush_lock` (asyncio lock) is also created to serialize buffer flushes.

### 7. OpenAPI generation
`func_openapi_spec_generate` builds the OpenAPI spec from the live routes and stores it as `cache_openapi`, served at `/openapi.json`.

### 8. Periodic buffer flush (`func_postgres_buffers_flush_periodic`)
Starts `func_postgres_buffers_flush_periodic` as `postgres_buffer_flush_task`. Every **60 seconds**, it calls `func_postgres_buffer_flush` separately for the primary general buffer and the dedicated API-log buffer. The single-buffer helper acquires `postgres_buffer_flush_lock` and delegates to `func_postgres_create(mode="flush")`. Logs use primary when `config_log_db=None`, or the matching named pool otherwise. Primary and log failures are isolated so one failed destination does not block the other.

See [buffer.md](buffer.md) for the full buffering lifecycle and API examples.

---

## `yield` — Serving

Between startup and shutdown the app handles requests. Handlers read clients/caches off `app.state`; the middleware records API logs into the buffer that `func_postgres_buffers_flush_periodic` drains.

---

## Shutdown

Runs in reverse spirit of startup — drain, then disconnect — all wrapped so a failure in one step still lets the rest proceed.

### 1. Stop background work
Calls `func_async_tasks_cancel` for tracked `runtime_background_tasks` and `postgres_buffer_flush_task`, cancelling each group and waiting up to 5 seconds for clean completion.

### 2. Final buffer flush
Calls `func_postgres_buffer_flush` separately for the primary and API-log buffers. Each call acquires `postgres_buffer_flush_lock` and delegates to `func_postgres_create(mode="flush")`, so records accumulated since the last periodic flush are persisted before disconnect.

### 3. Close every client
Gracefully disconnects all initialized clients — HTTP, the primary and every named Postgres pool, Redis, MongoDB, MSSQL, S3/SNS/SES, OpenAI/Gemini, PostHog (shutdown + flush), Kafka (stop), RabbitMQ channel + connection, Redis producer, SFTP, and Azure Blob/Email — each guarded by a presence/capability check so `None` or already-closed clients are skipped.

---

## Why this design

- **Fail fast** — invalid config or an unreachable required service stops startup instead of surfacing as random 500s later.
- **Everything optional** — the `if config_* else None` pattern means a bare clone boots with zero services; features light up as you add config.
- **Fast requests** — schema, roles, and config live in memory; writes are buffered and flushed in the background.
- **Clean lifecycle** — pools and connections are deterministically opened on startup and drained/closed on shutdown.

---

📚 [Back to README](../readme.md)
