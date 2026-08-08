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

## Highlights

- 🔐 **Auth built in** — JWT tokens, password/OTP/Google login, and role-based access control.
- 🗃️ **Generic CRUD** — Create/read/update/delete any database table with filters, relations & pagination.
- ⚡ **Fast by default** — Per-endpoint response caching, rate-limiting, and buffered async writes.
- 🧩 **Pluggable architecture** — Enable Postgres, Redis, Mongo, S3, Azure, Kafka, RabbitMQ, Celery, or AI models on demand.
- 🛠️ **Admin & Dev toolkit** — Built-in SQL runner, AI SQL generation, data import, and live schema introspection.
- 📦 **Background workers** — Queue consumers and durable retries with Postgres or dedicated message brokers.
- 🧾 **Self-documenting** — Generated OpenAPI spec + built-in interactive API console at `/`.
- 🔧 **Extend without forking** — Add custom routes and logic in drop-in extension files (`config_extend.py`, `function_extend.py`).

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Structure](#structure)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

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

## Quickstart

With the server running and `config_postgres_url` set in `.env`:

```bash
# 1. Sign up (returns access_token)
curl -X POST http://localhost:8000/auth/signup-username-password \
  -H "Content-Type: application/json" \
  -d '{"role": 2, "username": "alice", "password": "secret123"}'

# 2. Create a row
curl -X POST "http://localhost:8000/my/object-create?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "hello atom", "type": 1}'

# 3. Read your rows
curl "http://localhost:8000/my/object-read?table=test" \
  -H "Authorization: Bearer <access_token>"
```

📖 Learn more in [auth.md](docs/auth.md) and [crud.md](docs/crud.md).

## Configuration

All configuration defaults live in `config.py`. Override settings without editing core files:

1. **Environment Variables (`.env`)** — For secrets and database connection strings.
2. **`config_extend.py`** — Drop-in module for programmatic configuration overrides.

### Sample `.env`

```env
config_postgres_url=postgresql://atom:123456@127.0.0.1:5432/postgres?sslmode=disable
config_postgres_url_read=postgresql://atom:123456@read-replica:5432/postgres?sslmode=disable
config_redis_url=redis://localhost:6379
config_redis_url_ratelimiter=redis://localhost:6379/1
config_redis_url_queue=redis://localhost:6379
config_mongodb_url=mongodb://localhost:27017
config_clickhouse_url=https://default:password@clickhouse.example.com:8443/default
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_celery_url=redis://localhost:6379
```

📖 See **[config.md](docs/config.md)** for the complete configuration reference.

### ⚠️ [Secrets to override in production](docs/prod.md)

Before deploying to production, ensure you override default system secrets in `.env`. See **[prod.md](docs/prod.md)** for the complete production security configuration checklist and **[security.md](docs/security.md)** for security guidelines.

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

📖 See **[about.md](docs/about.md)** for framework architecture and **[extend.md](docs/extend.md)** for extension patterns.

## Documentation

📖 **Getting Started & Architecture**
- [about.md](docs/about.md) — Framework architecture and request lifecycle.
- [config.md](docs/config.md) — Complete configuration reference.
- [prod.md](docs/prod.md) — Production environment configuration.
- [security.md](docs/security.md) — Hardening checklist and security model.

⚙️ **Framework Core & Middleware**
- [lifespan.md](docs/lifespan.md) — Startup/shutdown client initializations.
- [middleware.md](docs/middleware.md) — Request pipeline, authentication, and caching.
- [logs.md](docs/logs.md) — API logging & audit trails.
- [buffer.md](docs/buffer.md) — Buffered database write performance.

🚀 **Features & Storage**
- [auth.md](docs/auth.md) — Signup, authentication methods, OTP, and roles.
- [crud.md](docs/crud.md) — Generic database CRUD capabilities.
- [read.md](docs/read.md) — Advanced filtering, pagination, and sorting.
- [object.md](docs/object.md) — Practical object CRUD examples.
- [postgres.md](docs/postgres.md) — Primary & read-replica Postgres connections.
- [query.md](docs/query.md) — Multi-database query runners & AI SQL generator.
- [queue.md](docs/queue.md) — Asynchronous job queues (Redis, RabbitMQ, Kafka, Celery).
- [messaging.md](docs/messaging.md) — Direct messaging & notifications system.
- [blob.md](docs/blob.md) — AWS S3 & Azure Blob storage integration.
- [comms.md](docs/comms.md) — Email (SES/Resend/Azure) and SMS (SNS/Fast2SMS).
- [admin.md](docs/admin.md) — Admin toolkit, data imports, and schema utilities.
- [workers.md](docs/workers.md) — Background workers and retry patterns.

🧱 **Customization & Guides**
- [guideline.md](docs/guideline.md) — Step-by-step guide to adding custom APIs.
- [router.md](docs/router.md) — Router design conventions.
- [extend.md](docs/extend.md) — Extending Atom without forking core code.
- [faq.md](docs/faq.md) — Frequently asked questions and solutions.

## Contributing

Contributions are welcome! Extend functionality via `config_extend.py` and `function_extend.py` so downstream projects remain updateable via `sync.py`.

Check out open issues and PRs at [github.com/atom36942/atom](https://github.com/atom36942/atom).

## License

Released under the [MIT License](LICENSE).
