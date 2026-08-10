# 🧭 About Atom Architecture & Technical Deep-Dive

Welcome to the technical single-source-of-truth architecture reference for **Atom**. This document explains how Atom is built under the hood, how its code layers interact, how connection pools and lifespans operate, and how HTTP requests flow through its single-middleware pipeline.

For high-level feature overviews, installation guides, and quickstart commands, see the **[README](../readme.md)**.

---

## 💡 Architecture & Design Principles

Atom is a batteries-included, opinionated FastAPI framework built for performance, modularity, and easy downstream maintenance:

- **Config-Driven & Optional Everything**: Core dependencies (Postgres, Redis, Mongo, S3, Azure, Kafka, RabbitMQ, Celery, AI models) are completely optional. Integrations activate only when their connection URLs or keys are present in **[config.py](config.md)** or `.env`.
- **Pure Async Architecture**: Built on FastAPI, Starlette, Uvicorn, `asyncpg`, `aioredis`, and `aiohttp` to maximize non-blocking concurrency.
- **Flat & Transparent Layering**: Avoids heavy ORM abstractions or scattered middleware classes. Core execution flows through `main.py` (framework runtime) and `function.py` (pure helper logic).
- **Non-Forking Extensibility**: Maintainers can extend routes and logic via drop-in extension files (`config_extend.py`, `function_extend.py`) without mutating core framework files, enabling seamless upstream updates via `sync.py`. Learn more in **[extend.md](extend.md)**.

---

## ⚙️ Core Technical Components & Layering

The codebase is organized into flat, specialized components with clear separation of responsibilities:

```
atom/
├── main.py         # App runtime, lifespan connection pools & single HTTP middleware
├── function.py     # Framework-agnostic pure logic, helpers & database engines
├── config.py       # Centralized declarative settings, rules & schema definitions
├── router/         # Access-tiered API endpoint handlers (auth, my, public, private, admin)
├── static/         # Served assets and built-in interactive API console
├── script/         # Standalone background queue workers & maintenance processes
└── sync.py         # Upstream framework updater tool
```

### 1. `main.py` — Application Core & Runtime
Assembles the FastAPI application instance. Handles the startup/shutdown **[lifespan](lifespan.md)** context manager, orchestrates connection pools (**[postgres.md](postgres.md)**, **[redis.md](redis.md)**), builds in-memory caches, registers routers (**[router.md](router.md)**), and mounts the unified **[middleware](middleware.md)**.

### 2. `function.py` — Helper Logic & Utility Engine
Contains all reusable, framework-agnostic helper functions (JWT token parsing, password hashing, generic CRUD operations, buffer flushes, blob operations, and AI utilities). See **[object.md](object.md)**, **[auth.md](auth.md)**, and **[query.md](query.md)**.

### 3. `config.py` — Centralized Declarative Configuration
Acts as the single source of truth for all environment variables, feature flags (`config_is_*`), token/OTP settings, and limits (upload size, batch size, read limits, buffer sizes), and endpoint permissions. Read the full reference in **[config.md](config.md)**.

### 4. `router/` — Access-Tiered Routers
API routes are partitioned into access tiers based on security requirements:
- `auth`: Signup, login, password reset, OTP, and OAuth endpoints (**[auth.md](auth.md)**).
- `my`: Authenticated user operations, profile settings, user object CRUD, and messaging (**[object.md](object.md)**, **[messaging.md](messaging.md)**).
- `public`: Unauthenticated public data reads and public forms (**[read.md](read.md)**).
- `private`: Server-side actions like internal emails and signed storage URLs (**[blob.md](blob.md)**, **[comms.md](comms.md)**).
- `admin`: High-privilege administrative utilities, query runners, data imports, and schema inspection (**[admin.md](admin.md)**).

See **[router.md](router.md)** for endpoint design conventions.

### 5. `script/` — Standalone Queue Workers
Contains consumer processes that execute independently of the web application server to process queued tasks (Postgres writes, email dispatch, resume parsing, user deletion cleanup). Read **[workers.md](workers.md)** and **[queue.md](queue.md)**.

---

## 🔄 Application Lifespan & Connection Management

The application lifecycle in `main.py` manages startup and shutdown routines cleanly using Python's `asynccontextmanager`.

```
Startup (lifespan)
  ├── 1. Connect Primary & Read-Replica Postgres Pools (asyncpg)
  ├── 2. Connect Redis Clients (Cache, Rate Limiter, Queue)
  ├── 3. Initialize Optional Clients (MongoDB, MSSQL, S3, Azure, Kafka, RabbitMQ)
  ├── 4. Load In-Memory Schema, Roles & Config Caches
  └── 5. Start Background Periodic Tasks (Buffered Writes Flush Loop)
```

For complete technical details on connection parameters, pooling strategies, and graceful shutdown sequences, see:
- **[lifespan.md](lifespan.md)** — Comprehensive lifespan lifecycle documentation.
- **[postgres.md](postgres.md)** — Postgres connection pool, primary/replica routing, and SSL configurations.
- **[redis.md](redis.md)** — Redis client isolation for cache, rate limiting, and queue management.

---

## ⚡ Request Lifecycle & Middleware Pipeline

Every HTTP request to Atom passes through a single, highly-optimized HTTP middleware defined in `main.py` (`@app.middleware("http")`), delegating logic processing to `function.py`:

```
Incoming Request
  │
  ├── 1. Token Decoding (func_token_decode)
  ├── 2. Auth Check (func_middleware_check_token)
  ├── 3. Role-Based Access Check (func_middleware_check_role)
  ├── 4. User Deactivation & Deletion Guard (func_middleware_check_user_*)
  ├── 5. Distributed Rate Limiter Check (func_middleware_check_ratelimiter)
  ├── 6. Response Cache Lookup (func_middleware_api_cache) ──[CACHE HIT]──▶ Return Cached Response
  │                                                                            │ [CACHE MISS]
  ├── 7. Endpoint Handler Execution (router/...)                              │
  ├── 8. Store Response in Cache (if configured) ◀─────────────────────────────┘
  ├── 9. Buffer API Audit Log Row (async-flushed to Postgres log_api table)
  │
  └── Output HTTP Response
```

For detailed specifications on each middleware phase, status code handling, and cache keys:
- Read **[middleware.md](middleware.md)** for full pipeline mechanics.
- Read **[auth.md](auth.md)** for token security and role enforcement.
- Read **[logs.md](logs.md)** for audit trail logging and request telemetry.

---

## 🗃️ Data, Query & Asynchronous Buffer Engines

Atom provides powerful built-in data handling abstractions without forcing heavy ORM overhead:

1. **Generic CRUD Engine**: Perform low-level CRUD operations against any SQL table using declarative configuration. See **[object.md](object.md)**.
2. **Advanced Filtering & Pagination Engine**: Parse complex queries, field selections, sorting parameters, and relational joins dynamically. Read **[read.md](read.md)**.
3. **High-Performance Async Write Buffer**: Non-blocking in-memory buffer that batches database writes (like request logging and analytics) into periodic bulk inserts to reduce database round-trips. Read **[buffer.md](buffer.md)**.
4. **Multi-Database & AI Query Runner**: Direct raw SQL query execution across Postgres, MSSQL, and ClickHouse with natural language AI SQL generation. See **[query.md](query.md)**.

---

## 📦 Workers, Storage & External Services

For complex background processing and external service integrations, Atom provides dedicated modules:

- **Asynchronous Task Queues**: Pluggable background queue architectures powered by Redis, RabbitMQ, Kafka, or Celery. See **[queue.md](queue.md)** and **[workers.md](workers.md)**.
- **Cloud Storage Integration**: Unified file upload, download preview, and SAS token generation for AWS S3 and Azure Blob Storage. Read **[blob.md](blob.md)**.
- **Communications Engine**: Transmit transactional emails (AWS SES, Resend, Azure) and SMS (AWS SNS, Fast2SMS). Read **[comms.md](comms.md)**.
- **Direct Messaging System**: Built-in user-to-user messaging and notification pipelines. Read **[messaging.md](messaging.md)**.

---

## 🛡️ Security, Admin & Extension Architecture

Atom is designed to remain secure in production and easy to update downstream:

- **Admin Operations & Introspection**: Schema management, administrative SQL runners, and system data import tooling. Read **[admin.md](admin.md)**.
- **Security & Hardening**: Strict role checks, token secret key rotation, SQL injection safeguards, and input sanitization. Read **[security.md](security.md)** and **[prod.md](prod.md)**.
- **Extending Without Forking**: Add custom routes or override core logic in `config_extend.py` and `function_extend.py`, keeping core framework updates simple via `sync.py`. Read **[extend.md](extend.md)** and **[faq.md](faq.md)**.
- **Troubleshooting & FAQs**: Answers to common developer questions, step-by-step API creation guidelines, performance tweaks, and deployment scenarios. Read **[faq.md](faq.md)**.

---

## 📚 Complete Technical Documentation Sitemap

| Area | Documentation File | Purpose / Contents |
| :--- | :--- | :--- |
| **Architecture** | **[about.md](about.md)** | Technical master guide & request lifecycle |
| **Configuration** | **[config.md](config.md)** | Centralized configuration dictionary & default reference |
| **Lifespan** | **[lifespan.md](lifespan.md)** | Application startup/shutdown, client pools & memory caches |
| **Middleware** | **[middleware.md](middleware.md)** | HTTP middleware pipeline, authentication & rate limiting |
| **Postgres** | **[postgres.md](postgres.md)** | Primary/replica pool setup, connection limits & asyncpg |
| **Redis** | **[redis.md](redis.md)** | Redis cache, rate limiter, and queue client management |
| **Object CRUD Engine** | **[object.md](object.md)** | Generic CRUD engine & access-tiered object CRUD APIs |
| **Read Engine** | **[read.md](read.md)** | Filtering, pagination, field selection & dynamic joins |
| **Write Buffer** | **[buffer.md](buffer.md)** | High-throughput asynchronous write buffer & flush loops |
| **Query Engine** | **[query.md](query.md)** | Raw SQL query execution & AI SQL query generation |
| **Authentication** | **[auth.md](auth.md)** | JWT auth, role enforcement, OTP & Google OAuth |
| **Queue System** | **[queue.md](queue.md)** | Background job queues (Redis, RabbitMQ, Kafka, Celery) |
| **Workers** | **[workers.md](workers.md)** | Consumer execution scripts in `script/` |
| **Cloud Storage** | **[blob.md](blob.md)** | AWS S3 and Azure Blob storage integration |
| **Communications**| **[comms.md](comms.md)** | Transactional email (SES/Resend/Azure) & SMS (SNS) |
| **Messaging** | **[messaging.md](messaging.md)** | User-to-user direct chat & notification queues |
| **Admin Toolkit** | **[admin.md](admin.md)** | Administrative ops, schema inspector & data import |
| **Router Design** | **[router.md](router.md)** | Access tier router conventions (`auth`, `my`, `admin`, etc.) |
| **API Logging** | **[logs.md](logs.md)** | Audit logging & HTTP request telemetry |
| **Extending Atom** | **[extend.md](extend.md)** | Non-forking extension via `config_extend.py` & `sync.py` |
| **Web Interfaces** | **[html.md](html.md)** | Built-in web interfaces (API Master & PgWeb) |
| **Security** | **[security.md](security.md)** | Production security model & hardening checklist |
| **Production** | **[prod.md](prod.md)** | Production deployment configuration checklist |
| **FAQ & Guides** | **[faq.md](faq.md)** | Step-by-step developer guidelines & operational answers |

---

📚 [Back to README](../readme.md)
