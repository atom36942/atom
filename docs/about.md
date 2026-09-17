# 🧭 Architecture, Lifespan & Routers

Welcome to the comprehensive architecture guide for **Atom**. This document explains how Atom is built under the hood: its core design principles, codebase structure, application lifespan (startup/shutdown), the unified single-middleware HTTP pipeline, and router conventions for authoring new APIs.

---

## 1. Design Principles

Atom is a batteries-included, opinionated async Python framework built on top of **FastAPI**, **Starlette**, **Uvicorn**, and **asyncpg**:

- **Config-Driven & Optional Everything**: Core dependencies (PostgreSQL, Redis, Mongo, S3, Azure, Kafka, RabbitMQ, Celery, AI models) are completely optional. Integrations activate only when their connection URLs or keys are present in [`config.py`](config.md) or `.env`.
- **Pure Async Architecture**: Uses non-blocking drivers (`asyncpg`, `redis.asyncio`, `aiohttp`, `httpx`) to maximize concurrency and throughput.
- **Flat & Transparent Layering**: Avoids heavy ORM abstractions or scattered middleware classes. Execution flows cleanly through `main.py` (runtime) and `function.py` (pure functions).
- **Non-Forking Extensibility**: Maintainers can extend routes and logic via drop-in extension files (`config_extend.py`, `function_extend.py`) without mutating core framework files, enabling upstream updates via `sync.py`. Learn more in [`extend.md`](extend.md).

---

## 2. Codebase Layout & Layering

The codebase is organized into flat, specialized components with clear separation of responsibilities:

```
atom/
├── main.py         # App runtime, lifespan connection pools & single HTTP middleware
├── function.py     # Framework-agnostic pure logic, helpers & database engines
├── config.py       # Centralized declarative settings, rules & schema definitions
├── router/         # Access-tiered API endpoint handlers (auth, my, public, private, admin)
├── static/         # Static web assets & built-in API console
├── script/         # Standalone background queue workers & maintenance processes
├── sync.py         # Upstream framework updater tool
├── requirements.txt
└── Dockerfile
```

### Core Components:
1. **`main.py`**: Assembles the FastAPI app, orchestrates startup/shutdown pools via lifespan, mounts the unified HTTP middleware, and auto-discovers routers.
2. **`function.py`**: Contains framework-agnostic helper functions (JWT parsing, password hashing, generic CRUD, write buffers, cloud storage, AI utilities). Functions are written as pure functions with keyword-only arguments.
3. **`config.py`**: Single source of truth for all configurations, feature flags (`config_is_*`), token lifetimes, limits, table schemas, and route access control policies (`config_api`).
4. **`router/`**: Access-tiered routers organized by security scope:
   - `auth`: Signup, password logins, OTP verification, and OAuth.
   - `my`: Self-service endpoints for authenticated users scoped to `request.state.user["id"]`.
   - `public`: Unauthenticated public data reads and public forms.
   - `private`: Authenticated server-side actions (emails, signed upload URLs).
   - `admin`: High-privilege administrative utilities, raw SQL runners, data import tools.
5. **`script/`**: Standalone background workers that consume tasks (buffer flushes, queue polling, email dispatch).

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
1. **Validation (`func_check`)**: Validates that `config_api` is well-formed: every entry uses allowed keys (`id`, `is_token`, `user_check_*`, `cache`, `rate_limit`), flags are booleans, check modes are valid (`redis` / `realtime` / `inmemory` / `token`). Misconfiguration causes fast-fail.
2. **Filesystem Prep**: Resets the working `tmp/` scratch directory and ensures `secret/` exists.
3. **Client Initialization**: Initializes clients conditionally based on `.env` settings:
   - `client_password_hasher`: Argon2 password hasher.
   - `client_http`: Shared `httpx.AsyncClient`.
   - `client_postgres`: Primary `asyncpg` connection pool.
   - `client_postgres_dict`: Named connection pools for read replicas or dedicated databases (e.g. `client_postgres_dict["logs"]`).
   - `client_redis`, `client_redis_user_state`, `client_redis_ratelimiter`, `client_redis_producer`: Isolated Redis clients.
   - Optional: MongoDB (Motor), MSSQL, S3, Azure Blob, Kafka, RabbitMQ, Celery, PostHog, OpenAI, Gemini.
4. **Database Schema Init**: When `config_is_postgres_schema_init = True`, applies table schemas, indexes, and constraints from `config_postgres`, and seeds the root admin user (`admin` / `role: 1`).
5. **In-Memory Cache Building**: Preloads read-mostly metadata to avoid database hits during request routing:
   - `cache_postgres_schema`: Table and column definitions.
   - `cache_config`: Key-value settings from the `config` database table.
   - `cache_users_role`, `cache_users_deactivated`, `cache_users_deleted`: Backs in-memory auth checks.
   - Write buffers: `cache_postgres_buffer_create` and `cache_postgres_buffer_log_api`.
6. **Register on `app.state`**: All local `client_*`, `cache_*`, `config_*`, and `func_*` are bulk-mounted onto `app.state`, accessible in routes as `request.app.state.<name>`.
7. **Periodic Buffer Flush Loop**: Launches background task `func_postgres_buffer_flush_periodic_task` draining in-memory write buffers every `config_postgres_buffer_flush_auto_sec`.

### Shutdown Sequence:
1. **Stop Tasks (`func_app_tasks_stop`)**: Cancels runtime background tasks and periodic flush loops with a 5-second graceful window.
2. **Final Buffer Flush (`func_postgres_buffer_flush_all`)**: Acquires `postgres_buffer_flush_lock` and inserts all remaining pending records in `cache_postgres_buffer_create` and `cache_postgres_buffer_log_api`.
3. **Close Connections**: Gracefully disconnects all initialized database pools, Redis connections, HTTP clients, and message brokers.

---

## 4. Single HTTP Middleware Pipeline

Every HTTP request to Atom passes through **one** unified HTTP middleware in `main.py` (`@app.middleware("http")`). The middleware orchestrates cross-cutting concerns, delegating logic to pure functions:

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
  ├── 7. Response Cache Lookup (func_middleware_api_cache, mode="get")
  │      └── [HIT] ──▶ Return cached response immediately
  │
  ├── 8. Request Dispatch:
  │      ├── Background mode (?is_background=true) ──▶ Schedule & return 202
  │      └── Direct execution ──▶ Execute route handler (await api_function(request))
  │
  ├── 9. Error Handling (catches exceptions, formats envelope, logs to Sentry)
  ├── 10. Cache Store (stores response if route policy has cache enabled)
  ├── 11. API Audit Logging (buffers one log_api row into cache_postgres_buffer_log_api)
  ├── 12. Security Headers (attaches nosniff, DENY, strict-origin)
  └── Return HTTP Response
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
    if not app_state.client_postgres:                     # 2. Guard required clients
        raise Exception("postgres client not initialized")
        
    oq = await app_state.func_request_param_read(         # 3. Read & validate params
        request=request, mode="query", strict=False,
        param_specs=[{"name": "days", "type": "int", "required": True}]
    )
    
    async with app_state.client_postgres.acquire() as conn:
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

### Registering Route Policies (`config_api`):
By default, any unlisted route is public. To require authentication, rate limiting, or caching, add an entry to `config_api` (or `config_extend.py`):
```python
config_api["/my/report"] = {
    "id": 210,
    "is_token": True,
    "rate_limit": {"count": 100, "seconds": 60},
    "cache": {"mode": "inmemory", "ttl_sec": 30, "is_per_user": True}
}
```
