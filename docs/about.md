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

### `static/`, `script/`, `sync.py`
- **`static/`** serves HTML and assets at `/static`, including the built-in API console.
- **`script/`** holds standalone processes run outside the request cycle — queue consumers, batch ingestion/cleanup, resume parsing, user-deletion workers.
- **`sync.py`** fetches the latest core files from the upstream repo (`git fetch` + `checkout FETCH_HEAD`), updating the framework while leaving your extension files untouched.

## Request Lifecycle

Every request flows through a single middleware before reaching its handler:

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

## Key Features

- **Generic CRUD** — create/read/update/delete over any table without hand-writing endpoints, with relation fetching, group-by reads, and where-clause building.
- **Flexible auth** — JWT tokens with signup/login by password, email/mobile OTP, or Google; Argon2 password hashing; role, deactivation, and deletion checks enforced in middleware.
- **Read/write pool split** — separate Postgres read-replica and external pools, with automatic fallback to the primary when a replica isn't configured.
- **Buffered logging & writes** — API logs and high-volume inserts are buffered in memory and flushed to Postgres on an interval, keeping the request path fast.
- **Built-in caching & rate-limiting** — per-endpoint response caching and rate limits driven entirely by config.
- **Background execution** — any request can be dispatched to a background task, plus standalone queue consumers/workers via Kafka, RabbitMQ, Redis, or Celery.
- **Query runners & AI** — safe read/write query runners with CSV export, and OpenAI/Gemini-backed SQL generation.
- **WebSocket support** — a `/websocket` endpoint demonstrates real-time writes through the same CRUD layer.
- **Self-documenting** — OpenAPI spec generated at startup, plus a served API console at `/`.

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

- **Add endpoints** in `router/` — they're auto-registered by tier.
- **Add or override logic** via `function_extend.py`.
- **Add or override settings** via `config_extend.py`.
- **Enable an integration** simply by supplying its config — no code changes required.
