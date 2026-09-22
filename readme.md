# ⚛️ Atom

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/status-active-brightgreen?style=flat-square)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-6366f1?style=flat-square)

**Core:**
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Starlette](https://img.shields.io/badge/Starlette-2ba977?style=flat-square)
![Uvicorn](https://img.shields.io/badge/Uvicorn-2A6DB2?style=flat-square)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white)

**Data & storage:**
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)
![MSSQL](https://img.shields.io/badge/SQL_Server-CC2927?style=flat-square&logo=microsoftsqlserver&logoColor=white)
![Amazon S3](https://img.shields.io/badge/AWS_S3-569A31?style=flat-square&logo=amazons3&logoColor=white)
![Azure Blob](https://img.shields.io/badge/Azure_Blob-0078D4?style=flat-square&logo=microsoftazure&logoColor=white)

**Messaging & queues:**
![Kafka](https://img.shields.io/badge/Kafka-231F20?style=flat-square&logo=apachekafka&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=flat-square&logo=rabbitmq&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white)

**AI, ops & infra:**
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)
![Sentry](https://img.shields.io/badge/Sentry-362D59?style=flat-square&logo=sentry&logoColor=white)
![PostHog](https://img.shields.io/badge/PostHog-1D4AFF?style=flat-square&logo=posthog&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

**Batteries-included, opinionated FastAPI framework for shipping production backends fast.**

Atom gives you authentication, generic CRUD over any table, caching, rate-limiting, background workers, blob storage, and pluggable integrations out of the box — while staying fully extensible so updates never clobber your code. Every integration is optional and driven by `config.py`.

## About

- 🔐 **Auth built in** — JWT tokens, password/OTP/Google login, and role-based access control.
- 🗃️ **Generic CRUD** — Create/read/update/delete any database table with filters, relations & pagination.
- ⚡ **Fast by default** — Per-endpoint response caching, rate-limiting, and buffered async writes.
- 🧩 **Pluggable architecture** — Enable Postgres, Redis, Mongo, S3, Azure, Kafka, RabbitMQ, Celery, or AI models on demand.
- 🛠️ **Admin & Dev toolkit** — Built-in SQL runner, AI SQL generation, data import, and live schema introspection.
- 📦 **Background workers** — Queue consumers and durable retries with Postgres or dedicated message brokers.
- 🧾 **Self-documenting** — Generated OpenAPI spec + built-in interactive API console at `/`.
- 🔧 **Extend without forking** — Add custom routes and logic in drop-in extension files (`config_extend.py`, `function_extend.py`).

## Requirements

- **Python 3.11+**
- **Git**
- Optional database drivers for MSSQL support (**unixODBC** on Linux/macOS, **Microsoft ODBC Driver for SQL Server** on Windows).

## Installation

**Linux / macOS:**

```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn main:app --reload
```

**macOS + Homebrew (pinned Python):**

```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.14 -m venv venv   # adjust version to your Homebrew Python
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn main:app --reload
```

**Windows (Command Prompt / PowerShell):**

```cmd
git clone https://github.com/atom36942/atom.git
cd atom
python -m venv venv
venv\Scripts\pip install --upgrade pip
venv\Scripts\pip install -r requirements.txt
venv\Scripts\uvicorn main:app --reload
```

Server runs on **http://localhost:8000** (`/` built-in API console, `/health`, `/info`, `/openapi.json`).

*Or run with Docker (Cross-Platform):*
```bash
docker build -t atom .
docker run --rm -p 8000:8000 --env-file .env atom
```

## Configuration

All configuration defaults live in `config.py`. Override settings without editing core files:

1. **Environment Variables (`.env`)** — For secrets and database connection strings.
2. **`config_extend.py`** — Drop-in module for programmatic configuration overrides.

### Sample `.env`

```env
config_postgres_url=postgresql://postgres:postgres@localhost:5432/postgres
config_root_user_password="your-strong-root-password"
config_token_secret_key="your-secret-key-at-least-32-chars"
config_login_password="your-strong-login-password"
config_cors_allow_origins=["http://localhost:3000", "https://app.example.com"]
config_signup_allowed_roles=[5]
```

Boolean environment settings use case-insensitive `true` or `false`. The loader also accepts `1`/`0`, `yes`/`no`, and `on`/`off`, but `true`/`false` is the project convention.

### ⚠️ Secrets to override in production

Before deploying to production, ensure you override default system secrets in `.env` (refer to `docs/prod.md` and `docs/security.md`).

## Extensibility

Atom is designed to be extended without forking core framework files. Add custom routes, custom database schemas, and custom helper logic in drop-in extension files:

- **`config_extend.py`** — Custom configurations, table schema definitions, and API route rules.
- **`function_extend.py`** — Custom business logic and helper function overrides.

This decouples your application code from the framework core, enabling seamless upstream updates via `python sync.py`.

## Built-in Web Interfaces

Atom comes with zero-dependency, single-page web applications stored in `static/`:

- ⚡ **API Master** (`static/api.html`) — Interactive API console, endpoint inspector, cURL importer, response viewer, and WebSocket tester served at `/`.
- 🗃️ **PgWeb** (`static/pgweb.html`) — Built-in PostgreSQL database browser, schema inspector, and SQL query runner served at `/static/pgweb.html`.

## Structure

```
atom/
├── main.py         # FastAPI app entry point & client lifecycle
├── function.py     # Core application logic & helpers
├── config.py       # Single source of truth for config defaults
├── router/         # API endpoint routers grouped by access control
├── static/         # Static web assets & built-in API console
├── script/         # Background queue workers & maintenance tasks
├── sync.py         # Downstream updater tool
├── requirements.txt
└── Dockerfile
```

## Documentation

<details>
<summary><strong>Full Documentation Index</strong></summary>

<br>

📖 **Getting Started & Architecture**
- [quickstart.md](docs/quickstart.md) — 5-minute setup and CRUD walkthrough.
- [about.md](docs/about.md) — Framework architecture, request pipeline, lifespan & routers.
- [config.md](docs/config.md) — Configuration reference & dynamic `.env` discovery.
- [security.md](docs/security.md) — Security model, headers & production hardening checklist.

🚀 **Core Engines & Features**
- [auth.md](docs/auth.md) — Authentication, identities, user uniqueness & root superadmin.
- [crud.md](docs/crud.md) — Generic CRUD engine, `/my/*` ownership matrix & advanced queries.
- [ownership.md](docs/ownership.md) — Ownership conventions, operation-specific policies & `/my/*` enforcement.
- [database.md](docs/database.md) — PostgreSQL pools, read replicas, write buffers & API logs.
- [redis.md](docs/redis.md) — Multi-client Redis architecture & cache strategies.
- [queue.md](docs/queue.md) — Asynchronous job queues, background consumers & retry workers.
- [messaging.md](docs/messaging.md) — In-app messaging, notifications, transactional email & SMS.
- [storage.md](docs/storage.md) — S3 & Azure Blob object storage and secure presigned previews.

🧱 **Administration & Customization**
- [admin.md](docs/admin.md) — Admin toolkit, data imports & built-in web UI (API Master & PgWeb).
- [extend.md](docs/extend.md) — Extending Atom without forking core code & upstream sync.
- [faq.md](docs/faq.md) — Developer guidelines & frequently asked questions.

</details>

## Contributing

Contributions are welcome! Extend functionality via `config_extend.py` and `function_extend.py` so downstream projects remain updateable via `sync.py`.

Check out open issues and pull requests on GitHub.

## License

Released under the MIT License.
