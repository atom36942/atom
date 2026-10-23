# ⚛️ Atom

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
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
- 🔧 **Easy to customize** — Add custom routes and logic in `config_extend.py` and custom modules in `function_extend/`.

## Requirements

- **Python 3.14**
- **Git**

## Installation

Replace `<new-name>` in the commands below with your preferred folder name (without the angle brackets).

**macOS / Linux:**

Atom runs on Python 3.14, the same version as the `Dockerfile`. macOS needs [Homebrew](https://brew.sh); on Linux, skip the `brew` steps and install `python3.14` from your distribution. `python3 --version` shows your Mac's default Python, which can differ; Atom only uses `python3.14`. `rm -rf venv` removes an existing virtual environment before recreating it, so the same steps also move a project to a new Python.

```bash
git clone https://github.com/atom36942/atom.git <new-name>
cd <new-name>
brew update
brew list --versions | grep python
brew install python@3.14
python3 --version
python3.14 --version
rm -rf venv
python3.14 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn main:app --reload
```

**Windows (Command Prompt / PowerShell):**

```cmd
git clone https://github.com/atom36942/atom.git <new-name>
cd <new-name>
python -m venv venv
venv\Scripts\pip install --upgrade pip
venv\Scripts\pip install -r requirements.txt
venv\Scripts\uvicorn main:app --reload
```

Server runs on **http://localhost:8000** (`/` home page linking the built-in apps, `/static/api.html` API console, `/health`, `/info`, `/openapi.json`).

Start Atom from its own folder; `.env`, `static/` and `tmp/` are resolved from the folder it is started in.

*Or run with Docker (Cross-Platform):*
```bash
touch .env
docker build -t atom .
docker run --rm -p 8000:8000 --env-file .env atom
```

## Configuration

All configuration defaults live in `config.py`. Override settings without editing core files:

1. **Environment Variables (`.env`)** — For secrets and database connection strings.
2. **`config_extend.py`** — Drop-in module for programmatic configuration overrides.

### Sample `.env`

```env
config_postgres_url_master=postgresql://postgres:postgres@localhost:5432/postgres
config_root_user_password="your-strong-root-password"
config_token_secret_key="your-secret-key-at-least-32-chars"
config_signup_allowed_roles=[2]
config_is_pgweb_enabled=True
```

Boolean environment settings use case-insensitive `true` or `false`. The loader also accepts `1`/`0`, `yes`/`no`, and `on`/`off`, but `true`/`false` is the project convention.

**Production secrets:** Before deploying, override default system secrets in `.env`. See the [production hardening checklist](docs/security.md#5-production-hardening-checklist).

## Extend

Keep application-specific settings and logic in your own extension files:

- **`config_extend.py`** — Create this optional file in the project root to override configuration, define tables, and configure API routes. Its `config_*` values take precedence over `config.py`.
- **`router_extend/<name>.py`** — Add an endpoint in a router file with a module-level `APIRouter`.
- **`function_extend/<name>.py`** — Add custom business logic with unique `func_*` names; Atom loads these modules automatically.

Atom owns `docs/`, `router/`, and `function/`. Create your own `docs_extend/`, `router_extend/`, `function_extend/`, `script_extend/`, and `tests_extend/` folders as needed. Keep configuration overrides in `config_extend.py`. Sync leaves all extensions untouched. Keep `func_*` names unique; files starting with `_` are not auto-loaded.

Follow the complete flow: **1. add `config_extend.py` → 2. add a router file in `router_extend/` → 3. add a function file in `function_extend/`**. Restart Atom and call the endpoint to verify it.

See the [extension guide](docs/extend.md) for a complete working example, configuration, tables, and workers.

## Sync

Update Atom from the project root:

```bash
python3 sync.py
```

Sync fetches Atom's upstream `main`, installs the latest updater, and updates framework files. It completely replaces the contents of `docs/`, `router/`, `function/`, `script/`, `static/`, and `files/`, including removing local-only files. `config.py` and selected core files are replaced. The `*_extend/` folders, `config_extend.py`, and `.env` are preserved. In `requirements.txt`, the `# atom` section is reset to Atom's packages and your `# extend` section is kept; then `venv/` is rebuilt to match `requirements.txt` exactly, on the Python version in the `Dockerfile` (skipped when nothing changed; `--no-venv` skips it). Save your work in Git and stop the app before syncing, then restart it.

See [sync details and recovery](docs/sync.md) for update behavior and recovery instructions.

## Built-in Web Interfaces

Atom comes with zero-dependency, single-page web applications stored in `static/`:

- ⚡ **API Master** (`static/api.html`) — Interactive API console, endpoint inspector, cURL importer, response viewer, and WebSocket tester at `/static/api.html`; `/` lists every HTML app in `static/` and `static_extend/`.
- 💬 **Chat** (`static/chat.html`) — Reference client for the `/my/message-socket` live chat, served at `/static/chat.html`.
- 🗃️ **PgWeb** (`static/pgweb.html`) — Built-in PostgreSQL database browser, schema inspector, and SQL query runner served at `/static/pgweb.html`.

## Structure

```
atom/
├── main.py         # FastAPI app entry point & client lifecycle
├── function/       # Atom function modules
├── function_extend/ # Your function modules (optional)
├── router_extend/   # Your API routers (optional)
├── script_extend/   # Your workers (optional)
├── docs_extend/     # Your documentation (optional)
├── tests_extend/    # Your tests (optional)
├── config_extend.py # Your config overrides (optional)
├── files_extend/    # Your extra files: constants, param specs, sample JSON, prompts (optional)
├── static_extend/   # Your web assets, served at /static (optional)
├── files/          # Atom's shared data files
├── config.py       # Single source of truth for config defaults
├── router/         # API endpoint routers grouped by access control
├── static/         # Static web assets & built-in API console
├── script/         # Background queue workers & maintenance tasks
├── sync.py         # Downstream updater tool
├── requirements.txt
└── Dockerfile
```

## Documentation

Check code with `venv/bin/ruff check .` (rules in `ruff.toml`; `All checks passed!` means no problems).
Run regression tests with `venv/bin/python -m unittest discover -s tests -v`.
See [test coverage and setup](tests/README.md).

### Full Documentation Index

📖 **Getting Started & Architecture**

- [quickstart.md](docs/quickstart.md) — 5-minute setup and CRUD walkthrough.
- [about.md](docs/about.md) — Framework architecture, request pipeline, lifespan & routers.
- [config.md](docs/config.md) — Configuration reference & dynamic `.env` discovery.
- [security.md](docs/security.md) — Security model, headers & production hardening checklist.
- [audit.md](docs/audit.md) — Security audit findings, fixes, verification & remaining deployment checks.

🚀 **Core Engines & Features**

- [auth.md](docs/auth.md) — Authentication, identities, user uniqueness & root superadmin.
- [crud.md](docs/crud.md) — Generic CRUD, filters, relations, pagination & `/my/*` ownership rules.
- [ownership.md](docs/ownership.md) — Ownership conventions, operation-specific policies & `/my/*` enforcement.
- [database.md](docs/database.md) — PostgreSQL pools, schema management, SQL/AI queries, write buffers & API logs.
- [redis.md](docs/redis.md) — Redis clients, user state, response caching, rate limiting, queues & failure behavior.
- [queue.md](docs/queue.md) — Asynchronous job queues, background consumers & retry workers.
- [messaging.md](docs/messaging.md) — In-app messaging, notifications, transactional email & SMS.
- [storage.md](docs/storage.md) — Complete blob guide: S3/Azure uploads, previews, SAS, ownership, and deletion.
- [performance.md](docs/performance.md) — Load testing, profiling, slow queries, workers & pool sizing.

🧱 **Administration & Customization**

- [admin.md](docs/admin.md) — Admin toolkit, data imports & built-in web UI (API Master & PgWeb).
- [extend.md](docs/extend.md) — Complete config → router → function flow, tables & workers.
- [sync.md](docs/sync.md) — Framework updates, preserved files & recovery.
- [faq.md](docs/faq.md) — Developer guidelines & frequently asked questions.

## License

Released under the MIT License.
