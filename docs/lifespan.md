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
Before touching any resource, `func_check` validates that `config_api` is well-formed: every entry uses only allowed keys (`id`, `is_token`, `user_check_*`, `api_cache_sec`, `api_ratelimiting_times_sec`), flags are `0/1`, check `mode`s are valid (`redis` / `realtime` / `inmemory` / `token`), and ids/routes are consistent. A misconfigured API table stops the boot here.

### 2. Filesystem prep
Resets the working `tmp/` directory (removed if stale, then recreated) and ensures `secret/` exists — scratch space for uploads/temp artifacts and secret material.

### 3. Client initialization
Creates one client per configured integration. **Each is conditional** — if the relevant `config_*` value is unset, the client is `None` and that feature stays dormant. Highlights:

- **Password hasher & HTTP** — Argon2 `PasswordHasher` and a shared `httpx.AsyncClient` are always created.
- **Postgres** — one primary pool (`client_postgres`) is shared by all main-database reads and writes. An optional external Postgres pool is created separately.
- **Redis** — cache/rate-limit client and a separate queue-producer client.
- **Other datastores** — MongoDB (Motor), MSSQL write/read pools (with fallback).
- **Cloud/storage** — AWS S3 (async client + boto3 resource), SNS, SES; Azure Blob and Email.
- **AI** — OpenAI and Gemini clients.
- **Messaging** — Kafka producer (started here), RabbitMQ connection + channel, Celery producer.
- **Ops** — PostHog analytics, SFTP connection.

Connection pools are opened with sensible bounds (Postgres `min_size=5, max_size=20`; MSSQL `pool_recycle=60`).

### 4. Database schema init
When `config_is_enable_postgres_schema_init = 1` and Postgres is present, `func_postgres_schema_init` applies the declarative schema from `config_postgres` — creating extensions, tables, columns, indexes, and constraints, and seeding the root admin user (password hashed with Argon2). See [config.md](config.md#config_postgres) for what it reads.

### 5. Cache building
To keep the request path fast, several read-mostly datasets are loaded into memory once at startup:

- **Schema caches** — `cache_postgres_schema` (+ an AI-oriented variant, and external-DB variants), plus derived `..._table_list` and `..._column_list`. These let routers validate table/column names without hitting the DB.
- **Data caches** — `cache_config` (the `config` table), and `cache_users_role` / `cache_users_deactivated` / `cache_users_deleted`, which back the middleware's `inmemory`-mode auth checks.
- **Empty runtime caches** — `cache_ratelimiter`, `cache_api_response`, and `cache_postgres_buffer_create` (the in-memory write buffer) start empty and fill during operation.

### 6. Register on `app.state`
Every local variable named `client_*` or `cache_*` is bulk-assigned onto `app.state`, making all clients and caches reachable from routers as `request.app.state.<name>`. A `flush_lock` (asyncio lock) is also created to serialize buffer flushes.

### 7. OpenAPI generation
`func_openapi_spec_generate` builds the OpenAPI spec from the live routes and stores it as `cache_openapi`, served at `/openapi.json`.

### 8. Background flush loop (`pulse_flush`)
Starts a long-running task that, every **60 seconds**, acquires `flush_lock` and calls `func_postgres_create(mode="flush")` to persist buffered rows (API logs, high-volume inserts) to Postgres. This is what makes buffered writes durable without slowing individual requests. Errors are caught and logged so one bad flush doesn't kill the loop.

---

## `yield` — Serving

Between startup and shutdown the app handles requests. Handlers read clients/caches off `app.state`; the middleware records API logs into the buffer that `pulse_flush` drains.

---

## Shutdown

Runs in reverse spirit of startup — drain, then disconnect — all wrapped so a failure in one step still lets the rest proceed.

### 1. Stop background work
Cancels any tracked `runtime_background_tasks` (waiting up to 5s), then cancels the `pulse_flush` loop cleanly.

### 2. Final buffer flush
Acquires `flush_lock` and runs one last `func_postgres_create(mode="flush")` so no buffered rows are lost on exit.

### 3. Close every client
Gracefully disconnects all initialized clients — HTTP, Postgres pools, Redis, MongoDB, MSSQL, S3/SNS/SES, OpenAI/Gemini, PostHog (shutdown + flush), Kafka (stop), RabbitMQ channel + connection, Redis producer, SFTP, and Azure Blob/Email — each guarded by a presence/capability check so `None` or already-closed clients are skipped.

---

## Why this design

- **Fail fast** — invalid config or an unreachable required service stops startup instead of surfacing as random 500s later.
- **Everything optional** — the `if config_* else None` pattern means a bare clone boots with zero services; features light up as you add config.
- **Fast requests** — schema, roles, and config live in memory; writes are buffered and flushed in the background.
- **Clean lifecycle** — pools and connections are deterministically opened on startup and drained/closed on shutdown.

---

📚 [Back to README](../readme.md)
