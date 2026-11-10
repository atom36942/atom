# 🧭 Architecture, Lifespan & Routers

Welcome to the comprehensive architecture guide for **Atom**. This document explains how Atom is built under the hood: its core design principles, codebase structure, application lifespan (startup/shutdown), the unified single-middleware HTTP pipeline, and router conventions for authoring new APIs.

---

## 1. Design decisions

Atom is an opinionated async Python framework on **FastAPI**, **Starlette**, **Uvicorn** and **asyncpg**, for small teams building internal apps and APIs, much of the code written by AI agents. Each decision below says why, and what was chosen against, so a later change can check itself against the reason rather than "improve" something deliberate.

| Decision | Why | Not chosen |
|---|---|---|
| One rules file, `AGENTS.md`, the same in every project | One place to read; every project follows the same rules; it is short enough to read in full before any work | Rules spread across docs, per-project rule files (they drift apart) |
| Route policy in `config_api` (token, roles, user checks, cache, rate limit), enforced by one middleware before the route | A route's behaviour is visible in one place without opening its code; startup fails on a route without an entry, so nothing is unprotected by accident | Decorators or checks inside each route (easy to forget one, nothing to validate at startup) |
| Every function is `func_*`, keyword-only, unique across Atom and the project, called as `app_state.func_*` | One calling style in every file and project; one search finds any definition; a test swaps one function on the app's state; project functions register the same way as Atom's | Direct imports (each file differs in what it imports; tests patch module paths) |
| `sync.py` copies Atom's files into each project instead of installing a package | The framework's code is in the project, readable and searchable like its own; one command updates files, requirements and the venv; `*_extend` paths are never touched | A pip package (its code hidden in `venv/`, needs publishing and releases) |
| No tags or releases: projects always sync Atom's latest `main`, versioned by `ATOM_VERSION` (semver) | One maintainer, many projects: one line of history to keep working, CI on every push | Release branches and pinned versions (old versions to maintain in parallel) |
| All integrations installed in every project (`requirements.txt` `# atom`) | Any feature works by adding its `.env` line; no project fails on a missing package; storage is cheap | Optional extras per project (smaller venvs, but a missing-package failure mode and per-project package lists) |
| Integrations, databases and clients turn on by `.env` lines (`config_<db>_url_<name>`), opened once at startup and closed at shutdown | A new database or service is configuration, never code; app code never opens its own pools | Clients opened in feature code (leaked pools, one per request) |
| Tables only in `config_postgres`, created and updated at startup in one transaction | The schema is code, reviewed with the change that needs it; every environment converges on start; `script.schema_plan` previews the change, and production can make it a deliberate step (init off: startup only checks, `schema_plan --apply` changes) | Migration files (ordering and history to manage, environments drift when one is skipped) |
| Postgres only through asyncpg, rows through `func_postgres_create/read/update/delete` | Fast, explicit SQL; one helper checks columns, types and ownership in one round trip | An ORM (hidden queries, slower, a second way to reach the database) |
| User checks pick a mode per route (`token`, `redis`, `realtime`, `inmemory`) | Each route chooses its own trade-off between speed and freshness: admin and destructive routes `realtime`, busy reads `token` or `redis` | One global mode (either slow everywhere or stale everywhere) |
| One simple rule over exceptions, no backward-compatibility shims | Fewer cases to remember and test; a rename changes every caller at once | Aliases and deprecation paths (two ways to do one thing, forever) |
| Every list pages after a cursor (`after` in and out, `null` at the end; limit + 1 rows read), with an index matching each filter and sort | Every page costs the same at row 10 and row 10 million; a page only needs to know whether Next exists | A total `count(*)` (scans the table on every page) and a growing `OFFSET` (reads and discards every earlier row) |
| Every CSV export goes through one function per database (`func_<db>_export`): one read query, a cursor, streamed and gzipped, at most `config_export_limit` rows, no count first; the file is the data as stored (real column names, values as they are) | Constant memory for a million rows; one limit in one place; a project writes only its query; an export means the same thing everywhere and matches the database | CSV code per project, a size-based switch between ways of exporting, a count before the download (a second full query) |
| Atom shares the backend only; pages and their files are each project's own, guided by `docs/page.md` defaults | Projects choose their own look and build; a framework update never changes a page | Shared front-end files (every project's page changes with each sync) |
| Startup checks over runtime surprises | Bad config, a missing `config_api` entry, duplicate `func_*` names or a weak production secret stop startup with a plain message | Failing on the first request that hits the problem |

---

## 2. Codebase layout

```
atom/
├── main.py         # app, lifespan (opens and closes clients), the single middleware, router discovery
├── function/       # every func_*, one module per area (clients, auth, postgres_*, queues, storage, ...)
├── config.py       # every default config_*: settings, config_api, config_postgres (tables)
├── router/         # API routes by access scope: auth, my, public, private, admin, index
├── static/         # Atom's pages (API console, Monitor, pgweb) and their assets
├── script/         # scripts that work in every project: check, consumers, schema_plan, load_test, ...
├── files/          # read-only data (countries, currencies)
├── docs/           # these docs; AGENTS.md is the rules file
├── tests/          # Atom's tests (unittest), run by script.check and CI
├── sync.py         # updates a project from Atom's main
├── requirements.txt
└── Dockerfile
```

A project adds `*_extend` folders (`router_extend/`, `function_extend/`, `files_extend/`, `static_extend/`, `script_extend/`, `docs_extend/`, `tests_extend/`) and `config_extend.py`; sync never changes them. See [`extend.md`](extend.md).

---

## 3. Application Lifespan (`func_lifespan`)

Atom wires up its state in a single FastAPI **lifespan** context manager (`func_lifespan` in `main.py`). It runs once on **startup** (before `yield`) and once on **shutdown** (after `yield`).

```
STARTUP  → validate config → prepare directories → init client pools → apply schema
         → build in-memory caches → register on app.state → generate OpenAPI → start flush loop
  yield  (app serves requests)
SHUTDOWN → stop background tasks → final buffer flush → close every client
```

### Startup Sequence:
1. **Validation (`func_check`)**: Validates that `config_api` is well-formed: every entry uses allowed keys (`id`, `is_token`, `is_connection_param`, `user_check_*`, `cache`, `rate_limit`), flags are booleans, check modes are valid (`redis` / `realtime` / `inmemory` / `token`). Misconfiguration causes fast-fail.
2. **Filesystem Prep**: Ensures `tmp/` and `secret/` exist in the project folder (where `main.py` is; `venv/bin/python main.py` switches there first, so starting it from another folder changes nothing); wipes `tmp/` first only when `config_is_tmp_reset` is true (default false).
3. **Client Initialization**: Initializes clients conditionally based on `.env` settings:
   - `client_password_hasher`: Argon2 password hasher.
   - `client_http`: Shared `httpx.AsyncClient`.
   - `client_postgres_dict`: One pool per named database from `config_postgres_url_<name>`; `client_postgres_dict["master"]` is the default (e.g. `client_postgres_dict["logs"]` for a dedicated log database).
   - `client_redis_dict`: one isolated Redis client per `config_redis_url_<name>`, read by role (`api_response`, `user_state`, `ratelimiter`, `queue`) or by a project's own name.
   - Optional: MongoDB (Motor), MSSQL, S3, Azure Blob, Kafka, RabbitMQ, Celery, PostHog, OpenAI, Gemini.
4. **Database Schema Init**: When `config_is_postgres_schema_init = True`, applies table schemas, indexes, and constraints from `config_postgres`, and seeds the root admin user (`admin` / `role: 1`). When `False`, only compares, and stops startup if the database differs (`script.schema_plan --apply` runs the changes).
5. **In-Memory Cache Building**: Preloads read-mostly metadata to avoid database hits during request routing:
   - `cache_postgres_schema`: Table and column definitions.
   - `cache_config`: Key-value settings from the `config` database table.
   - `cache_users_role`, `cache_users_deactivated`, `cache_users_deleted`: Backs in-memory auth checks.
   - Write buffers: `buffer_postgres_create` and `buffer_postgres_log_api`.
6. **Register on `app.state`**: All local `client_*`, `cache_*`, `buffer_*`, `config_*`, and `func_*` are bulk-mounted onto `app.state`, accessible in routes as `request.app.state.<name>`.
7. **Periodic Tasks (`func_app_tasks_start`)**: Launches the buffer flush loop (`func_postgres_buffer_flush_periodic_task`, every `config_postgres_buffer_flush_auto_sec`), OTP and `log_api` retention cleanup, and in-memory cache cleanup; `func_app_tasks_stop` cancels them at shutdown.

### Shutdown Sequence:
1. **Stop Tasks (`func_app_tasks_stop`)**: Cancels runtime background tasks and periodic flush loops with a 5-second graceful window.
2. **Final Buffer Flush (`func_postgres_buffer_flush_all`)**: Acquires `runtime_lock_postgres_buffer_flush` and inserts all remaining pending records in `buffer_postgres_create` and `buffer_postgres_log_api`.
3. **Close Connections**: Gracefully disconnects all initialized database pools, Redis connections, HTTP clients, and message brokers.

---

## 4. Single HTTP Middleware Pipeline

Every HTTP request to Atom passes through **one** unified plain ASGI middleware in `main.py` (`app.add_middleware(middleware)`; about a third faster than `@app.middleware("http")`, see [performance.md](performance.md#7-asgi-middleware)). WebSockets skip it. The middleware orchestrates cross-cutting concerns, delegating logic to pure functions:

```
Request
  │
  ├── 0. OPTIONS short-circuit (passes to CORSMiddleware)
  ├── 1. Initialize request timer & state (request.state.user = {})
  ├── 2. Look up route policy in config_api (or default public)
  ├── 3. Active Check (reject if is_active=False)
  ├── 4. Decode JWT Token (func_token_decode -> request.state.user)
  ├── 5. Auth & User-State Checks:
  │      ├── Token check (is_token=True)
  │      ├── Role check (user_check_role)
  │      ├── Deactivated check (user_check_deactivated)
  │      └── Deleted check (user_check_deleted)
  ├── 6. Distributed Rate Limiter Check (func_middleware_check_ratelimiter)
  ├── 7. Postgres Selection (func_middleware_postgres_select -> request.state.client_postgres, request.state.cache_postgres_schema; master, or ?connection= when is_connection_param=True)
  ├── 8. Response Cache Lookup (func_middleware_api_cache, mode="get")
  │      └── [HIT] ──▶ Return cached response immediately
  │
  ├── 9. Request Dispatch:
  │      ├── Background mode (?is_background=true) ──▶ Schedule & return 202
  │      └── Direct execution ──▶ Execute route handler inline (await asgi_app(scope, receive, send_wrapped))
  │
  ├── 10. Error Handling (catches exceptions, formats envelope, logs to Sentry)
  ├── 11. Cache Store (stores a 200 body if route policy has cache enabled)
  ├── 12. Security Headers (added by the wrapped send on every response)
  └── 13. API Audit Logging (after the response is sent, buffers one log_api row into buffer_postgres_log_api)
```

### Baseline Security Headers Attached:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-XSS-Protection: 0`

---

## 5. Router Design & Writing APIs

Routers live in [`router/`](../router). Each file is auto-discovered and mounted at startup by `func_app_router_add`. Files load in the order set by `router_order` in `main.py` (`index → auth → my → public → private → admin`).

### Anatomy of an Endpoint:
```python
@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request: Request):
    app_state = request.app.state                         # 1. Grab app.state once
    if not request.state.client_postgres:                 # 2. Guard required clients (master, or ?connection= when is_connection_param)
        raise Exception("postgres client not initialized")
        
    oq = await app_state.func_request_param_read(         # 3. Read & validate params
        request=request, mode="query", strict=False,
        param_specs=[{"name": "days", "type": "int", "required": True}]
    )
    
    async with request.state.client_postgres.acquire() as conn:
        records = await conn.fetch(sql, oq["days"], request.state.user["id"])
        obj_list = [dict(r) for r in records]
        
    return {"status": 1, "message": obj_list}             # 4. Standard response envelope
```

### Naming Conventions:
| Element | Convention | Example |
| :--- | :--- | :--- |
| Route Path | `/<tier>/<action-kebab>` | `/my/object-create` |
| Handler Function | `func_api_<tier>_<action_snake>` | `func_api_my_object_create` |
| Signature | Keyword-only `request` | `async def func_api_...(*, request: Request)` |

### Parameter Extraction — `func_request_param_read`:
**Never** parse `request.query_params` or `request.json()` manually. Use `func_request_param_read`:
```python
oq = await app_state.func_request_param_read(
    request=request,
    mode="query",        # "query", "body", "form", or "header"
    strict=False,
    param_specs=[
        {"name": "table", "type": "str", "required": True},
        {"name": "limit", "type": "int", "default": 100},
        {"name": "mode", "type": "str", "allowed": ["now", "buffer"], "default": "now"},
    ]
)
```
- Supported types: `int`, `float`, `str`, `bool`, `dict`, `list`, `file`, `list:int`, `list:str`.
- Booleans automatically parse `"true"`, `"false"`, `1`, `0`, `"yes"`, `"no"`.

### Request Scopes:
- `request.app.state`: Process-wide application state (clients, caches, config, functions).
- `request.state`: Per-request state set by middleware (`request.state.user` holds decoded JWT claims).

### Standard Response Envelope:
```json
{"status": 1, "message": <data>}
```
- On errors, simply `raise Exception("error message")`. The middleware catches the exception, attaches traceback telemetry, and formats the standard error JSON.
- A plain `Exception` returns HTTP 400. When the status matters, raise `app_state.func_api_error(message="...", status_code=403)`; the body stays `{"status": 0, "message": ...}`. The middleware already returns 401 for missing, invalid, or expired tokens, 403 for role and account-status denials, 404 for disabled endpoints, 429 for rate limits, 500 for server misconfiguration, 409 for database deadlocks, 502 for failed external APIs, and 503 when Postgres or Redis is unreachable.

### Registering Route Policies (`config_api`):
By default, any unlisted route is public. To require authentication, rate limiting, or caching, add an entry to `config_api` (or `config_extend.py`):
```python
config_api["/my/report"] = {
    "id": 210,
    "is_token": True,
    "is_connection_param": True,
    "rate_limit": {"mode": "inmemory", "limit": 100, "window_sec": 60},
    "cache": {"mode": "inmemory", "ttl_sec": 30, "is_per_user": True}
}
```

## Developer extensions

Atom owns every unsuffixed folder (`docs/`, `router/`, `function/`, `script/`, `static/`, `files/`); sync fully replaces them. Use the matching `<name>_extend/` folders and `config_extend.py` for project-specific work. Extension functions are registered alongside core functions; extension routers load after core routers. Scripts run separately and docs are not loaded by the API. See [extensions](extend.md) and [sync](sync.md).
