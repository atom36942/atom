# 🧭 About Atom

This page is the architecture deep-dive: how Atom is put together, component by component, and how a request flows through it. For what Atom is, how to install it, and its feature highlights, start at the [README](../readme.md).

## Design Principles

- **Opinionated, not restrictive** — one clear convention for wiring clients, config, and routes, so you skip the boilerplate and start building features.
- **Config over code** — auth rules, roles, rate limits, caching, and schema live as data in `config.py`, not scattered through the codebase.
- **Everything optional** — each integration (Postgres, Redis, Mongo, S3, OpenAI, Kafka, …) activates only when its config is provided. No config, no client.
- **Extend without forking** — drop-in `function_extend.py` / `config_extend.py` modules override or add behavior without editing core files, so you can pull framework updates cleanly.

## Core Components

The repo is deliberately flat ([layout in the README](../readme.md#project-structure)). Each top-level piece has one job:

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

## Tech Stack

FastAPI + Starlette + Uvicorn, async throughout. Postgres/MSSQL via `asyncpg`/`aioodbc`, Redis, MongoDB (Motor), object storage on AWS S3 / Azure Blob, messaging via Kafka / RabbitMQ / Celery, AI via OpenAI & Gemini, plus PyJWT, Argon2, PostHog, and Sentry.

## Where to next

- **Feature guides** — [auth.md](auth.md), [crud.md](crud.md), [blob.md](blob.md), [comms.md](comms.md), [messaging.md](messaging.md), [admin.md](admin.md), [workers.md](workers.md).
- **Deep internals** — [lifespan.md](lifespan.md), [middleware.md](middleware.md).
- **Building on Atom** — [router.md](router.md), [extend.md](extend.md), [config.md](config.md), [security.md](security.md).

---

📚 [Back to README](../readme.md)
