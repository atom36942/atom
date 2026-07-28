# About Atom

Atom is an open-source, **opinionated FastAPI framework** for shipping production backends fast. It comes with authentication, generic CRUD, caching, rate-limiting, background jobs, blob storage, and a dozen pluggable integrations out of the box — while staying fully extensible, so developers keep complete freedom to add their own logic.

## Design Principles

- **Opinionated, not restrictive** — one clear convention for wiring clients, config, and routes, so you skip the boilerplate and start building features.
- **Config over code** — auth rules, roles, rate limits, caching, and schema live as data in `config.py`, not scattered through the codebase.
- **Everything optional** — each integration (Postgres, Redis, Mongo, S3, OpenAI, Kafka, …) activates only when its config is provided. No config, no client.
- **Extend without forking** — drop-in `function_extend.py` / `config_extend.py` modules override or add behavior without editing core files, so you can pull framework updates cleanly.

## Project Layout

```
atom/
├── main.py         # FastAPI app: lifespan, client init, middleware, routing
├── function.py     # All business/helper logic as pure functions
├── config.py       # Single source of configuration
├── router/         # API endpoints, grouped by access tier
├── static/         # Served HTML/assets (incl. built-in API console)
├── script/         # Standalone workers & jobs (queue consumers, batch tasks)
├── sync.py         # Pulls latest framework files from upstream
├── requirements.txt
└── Dockerfile
```

## Core Components

### `main.py` — Application core
Assembles and runs the app. On **startup** (lifespan) it initializes every configured client — Postgres (read/write pools), Redis, MongoDB, MSSQL, S3/SNS/SES, OpenAI, Gemini, Kafka, RabbitMQ, Celery, SFTP, Azure Blob/Email — builds in-memory caches (DB schema, user roles, config), runs optional schema init, and starts a background buffer-flush loop. It defines the single **HTTP middleware** (see lifecycle below), CORS, Sentry, static mounting, and auto-registers routers. On **shutdown** every client is closed and buffered writes are flushed.

### `function.py` — Pure logic
The framework's logic layer: token encode/decode, middleware checks, generic Postgres/MSSQL CRUD, query runners, schema readers, blob upload/preview/delete, OTP send/verify, email, AI query generation, OpenAPI spec generation, and more. Keeping these framework-agnostic makes them easy to test, reuse, and override.

### `config.py` — Configuration
One file for all settings, organized in sections:
- **Integrations** — connection URLs and API keys (all default to `None`).
- **System** — feature flags (`config_is_enable_*`), token/OTP settings, and limits (upload size, batch size, read limits, buffer sizes).
- **Table / Column / SQL** — declarative table definitions, column rules, and reusable SQL.
- **Per-tier API rules** — for each route: whether a token is required, role/deactivation/deletion checks, rate limits, and cache TTLs.

See [config.md](config.md) for a full, grouped reference of every key.

### `router/` — API endpoints
Endpoints are split by access tier and loaded in a fixed order:

| Tier | Purpose |
|------|---------|
| `index` | Root, health, info, `openapi.json` |
| `auth` | Signup & login — password, OTP (email/mobile), Google |
| `my` | The authenticated user's own data — profile, token refresh, object CRUD, messaging, blobs |
| `public` | Open endpoints — public reads/creates, OTP send/verify, converters |
| `private` | Server-side actions — send email, blob upload / SAS |
| `admin` | Privileged ops — DB/schema info, query runner, imports, AI query generation, sync |

### `static/` — Served assets
Serves HTML and static files at `/static`, including the built-in API console rendered at `/`.

### `script/` — Workers & jobs
Standalone processes run outside the request cycle — queue consumers, batch ingestion/cleanup, resume parsing, and user-deletion workers. Started as separate processes when needed.

### `sync.py` — Framework updater
Fetches the latest core files from the upstream repo (`git fetch` + `checkout FETCH_HEAD`), updating the framework while leaving your extension files (`config_extend.py`, `function_extend.py`, `.env`) untouched.

## Request Lifecycle

Every request flows through a single HTTP middleware — defined in [`main.py`](../main.py) (`@app.middleware("http")`) — before reaching its handler. The middleware only orchestrates; each step's logic lives in [`function.py`](../function.py):

```
Request
  → decode token
  → check auth · role · deactivation · deletion
  → rate-limit
  → cache lookup ──(hit)──▶ return cached response
       │(miss)
  → run handler  (or dispatch to background if requested)
  → store in cache
  → buffer an API log row (async-flushed to Postgres)
  → Response
```

| Step | Defined in (`function.py`) |
|------|----------------------------|
| Decode token | `func_token_decode` |
| Auth check | `func_middleware_check_auth` |
| Role check | `func_middleware_check_role` |
| Deactivation check | `func_middleware_check_user_deactivated` |
| Deletion check | `func_middleware_check_user_deleted` |
| Rate-limit | `func_middleware_check_ratelimiter` |
| Cache get/set | `func_middleware_api_cache` |
| Background dispatch | `func_middleware_api_background` |
| Error handling | `func_middleware_api_response_error` |
| API log buffer | `func_postgres_create` (`mode="buffer"`, `table="log_api"`) |

The interval flush of buffered logs/writes runs in the `pulse_flush` loop started by the lifespan in `main.py`.

## Key Features

- **Generic CRUD** — create/read/update/delete over any table without hand-writing endpoints, with relation fetching, group-by reads, and where-clause building. *(`func_postgres_create` / `_read` / `_update` / `_delete`, `func_postgres_relation`, `func_postgres_groupby_read`, `func_postgres_where_build` in `function.py`)*
- **Flexible auth** — JWT tokens with signup/login by password, email/mobile OTP, or Google; Argon2 password hashing; role, deactivation, and deletion checks enforced in middleware. *(`func_token_encode` / `_decode`, `func_auth_user_login_fetch`, `func_middleware_check_*` in `function.py`; endpoints in `router/auth.py`)*
- **Read/write pool split** — separate Postgres read-replica and external pools, with automatic fallback to the primary when a replica isn't configured. *(`client_postgres_read_fallback` in `main.py`)*
- **Buffered logging & writes** — API logs and high-volume inserts are buffered in memory and flushed to Postgres on an interval, keeping the request path fast. *(`pulse_flush` loop in `main.py`, `func_postgres_create` buffer mode)*
- **Built-in caching & rate-limiting** — per-endpoint response caching and rate limits driven entirely by config. *(`func_middleware_api_cache`, `func_middleware_check_ratelimiter`; rules in `config.py`)*
- **Background execution** — any request can be dispatched to a background task, plus standalone queue consumers/workers via Kafka, RabbitMQ, Redis, or Celery. *(`func_middleware_api_background`, `func_producer`, `func_run_broker`; workers in `script/`)*
- **Query runners & AI** — safe read/write query runners with CSV export, and OpenAI/Gemini-backed SQL generation. *(`func_postgres_query_runner_*`, `func_mssql_query_runner_*`, `func_postgres_query_generator_ai` in `function.py`)*
- **WebSocket support** — a `/websocket` endpoint demonstrates real-time writes through the same CRUD layer. *(`router/index.py`)*
- **Self-documenting** — OpenAPI spec generated at startup, plus a served API console at `/`. *(`func_openapi_spec_generate` in `function.py`)*

## Tech Stack

FastAPI + Starlette + Uvicorn, async throughout. Postgres/MSSQL via `asyncpg`/`aioodbc`, Redis, MongoDB (Motor), object storage on AWS S3 / Azure Blob, messaging via Kafka / RabbitMQ / Celery, AI via OpenAI & Gemini, plus PyJWT, Argon2, PostHog, and Sentry.

## Getting Started

See [setup.md](setup.md) for full installation, configuration, running, Docker, workers, and update instructions. In short:

```bash
git clone https://github.com/atom36942/atom.git && cd atom
python3 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/uvicorn main:app --reload
```

Provide only the integration config you need (e.g. `config_postgres_url`, `config_redis_url`); everything else stays dormant.

## Extending Atom

Atom is built to be extended without editing core files, so framework updates via `sync.py` never clobber your work:

- **Add endpoints** in `router/` — auto-registered on startup.
- **Add or override logic** via `function_extend.py`.
- **Add or override settings** via `config_extend.py`.
- **Enable an integration** simply by supplying its config — no code changes required.

See [extend.md](extend.md) for the full guide, including adding tables, workers, and updating the framework with `sync.py`.

---

📚 [Back to README](../readme.md)
