# ⚛️ Atom

**Batteries-included, opinionated FastAPI framework for shipping production backends fast.**

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

Atom gives you authentication, generic CRUD over any table, caching, rate-limiting, background workers, blob storage, and a dozen pluggable integrations (Postgres, Redis, Mongo, S3/Azure, Kafka/RabbitMQ/Celery, OpenAI/Gemini) out of the box — while staying fully extensible, so you keep complete freedom to add your own logic. Every integration is optional (it activates only when its config is set), behavior is driven by data in `config.py`, and you extend the framework via drop-in modules so updates never clobber your code.

## Highlights

- 🔐 **Auth built in** — JWT tokens; login by password, email/mobile OTP, or Google; role-based access.
- 🗃️ **Generic CRUD** — create/read/update/delete any table with filters, relations & pagination — no per-table code.
- ⚡ **Fast by default** — per-endpoint response caching, rate-limiting, and buffered writes off the hot path.
- 🧩 **Pluggable everything** — swap Postgres/Redis/Mongo/S3/Azure/Kafka/RabbitMQ/Celery/OpenAI/Gemini via config.
- 🛠️ **Admin toolkit** — SQL query runners, AI-generated SQL, data imports, schema introspection.
- 📦 **Background workers** — queue consumers and a durable retry pattern using just Postgres.
- 🧾 **Self-documenting** — OpenAPI spec + a built-in API console at `/`.
- 🔧 **Extend without forking** — drop-in `config_extend.py` / `function_extend.py`; update with `sync.py`.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Background workers](#background-workers)
- [Updating Atom](#updating-atom)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Requirements

- **Python 3.11+** (the Docker image uses 3.11; the venv flow works on newer versions too)
- **Git**
- For MSSQL support: the **unixODBC** system libraries (`unixodbc unixodbc-dev`) — already installed in the Docker image
- Optional services you plan to enable: Postgres, Redis, MongoDB, etc.

Atom needs **no service to boot** — every integration is optional. A bare clone runs; features light up as you add config.

## Installation

```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv                    # create a virtual environment
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt   # install dependencies
```

**macOS + Homebrew (pinned Python)** — using a specific Homebrew Python and starting from a clean venv:

```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.14 -m venv venv
./venv/bin/python --version           # confirm the interpreter
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/python main.py               # or: venv/bin/uvicorn main:app --reload
```

Adjust `python3.14` to the Homebrew version you have (`brew install python@3.12`, etc.).

### Run

```bash
venv/bin/uvicorn main:app --reload   # development, auto-reload on file changes
venv/bin/python main.py              # or run directly (reads PORT, defaults to 8000)
```

The server starts on **http://localhost:8000**. Useful endpoints:

- `/` — built-in API console (served HTML)
- `/health` — health check
- `/info` — live API list, DB schema, and config
- `/openapi.json` — generated OpenAPI spec

### Docker

```bash
docker build -t atom .                              # build the image
docker run --rm -p 8000:8000 --env-file .env atom   # run it, injecting your .env config
```

The image installs ODBC drivers and all dependencies, then runs `python main.py` on port 8000.

## Quickstart

With the server running and `config_postgres_url` set, here's the full loop — sign up, get a token, create a row, read it back:

```bash
# 1. Sign up → returns { access_token, refresh_token, ... }
curl -X POST http://localhost:8000/auth/signup-username-password \
  -H "Content-Type: application/json" \
  -d '{"role": 2, "username": "alice", "password": "secret123"}'

# 2. Create a row (use the access_token from step 1)
curl -X POST "http://localhost:8000/my/object-create?table=test" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "hello atom", "type": 1}'

# 3. Read your rows
curl "http://localhost:8000/my/object-read?table=test" \
  -H "Authorization: Bearer <access_token>"
# → {"status": 1, "message": {"obj_list": [...], "has_next_page": false}}
```

Every response uses the same envelope: `{"status": 1, "message": ...}`. See [auth.md](docs/auth.md) and [crud.md](docs/crud.md) for the full picture.

## Configuration

All settings live in `config.py` and default to safe values (integrations default to `None`, i.e. off). Override them **without editing `config.py`** in two ways:

1. **Environment variables / `.env`** — for secrets and connection strings. Create a `.env` file in the project root:

   ```bash
   config_postgres_url=postgresql://atom:123456@127.0.0.1:5432/postgres?sslmode=disable
   config_postgres_url_read=postgresql://atom:123456@read-replica:5432/postgres?sslmode=disable
   config_redis_url=redis://localhost:6379
   config_redis_url_ratelimiter=redis://localhost:6379/1
   config_redis_url_queue=redis://localhost:6379
   config_mongodb_url=mongodb://localhost:27017
   config_rabbitmq_url=amqp://guest:guest@localhost:5672
   config_celery_url=redis://localhost:6379
   ```

   `.env` is git-ignored — keep your secrets there. Only set what you need; unset integrations stay dormant.

2. **`config_extend.py`** — a git-ignored, drop-in module for overriding or adding any config value in code. Add `function_extend.py` the same way to override or extend logic. Both are auto-loaded if present, so framework updates via `sync.py` never clobber your customizations.

Any environment variable named `config_postgres_url_<name>` creates a named PostgreSQL pool that supported read APIs can select with `?db=<name>`. When `db` is omitted, the primary `config_postgres_url` pool is used. See [postgres.md](docs/postgres.md) for configuration, supported APIs, examples, and production sizing; see [config.md](docs/config.md) for the complete configuration reference.

### ⚠️ Secrets to override in production

All integration keys default to `None` (off), but two system values ship with **insecure defaults** in `config.py`. Override both before any real deployment — add them to your `.env`:

```bash
config_token_secret_key=<a-long-random-string>
config_root_user_password=<a-strong-password>
```

| Key | Default in `config.py` | Why it matters |
|-----|------------------------|----------------|
| `config_token_secret_key` | `mysecretkey-mysecretkey-mysecretkey` | Signs every JWT — if left default, anyone can forge auth tokens. |
| `config_root_user_password` | `123456` | Password for the seeded root (role 1) admin user. |

Generate a strong token secret with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Project structure

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

See [about.md](docs/about.md) for how these fit together.

## Background workers

Standalone processes in `script/` run outside the API — start them as separate processes when you need queue consumers or batch jobs:

```bash
venv/bin/python script/consumer_postgres_create.py   # queue consumer: applies queued creates
venv/bin/python script/worker_resume_parser.py        # table-poller worker with retries
```

These rely on a configured queue backend (`config_redis_url_queue`, `config_rabbitmq_url`, `config_kafka_url`, or `config_celery_url`). See [workers.md](docs/workers.md).

## Updating Atom

`sync.py` pulls the latest framework files from upstream while leaving your `.env`, `config_extend.py`, and `function_extend.py` untouched:

```bash
venv/bin/python sync.py
```

It fetches `main`, then checks out the core files (`main.py`, `function.py`, `config.py`, routers, `static/api.html`, `Dockerfile`, etc.). `requirements.txt` is only pulled if you don't already have one — re-run the install step afterward if it changes.

## Documentation

📖 **Getting started**

| Page | What's inside |
|------|---------------|
| [about.md](docs/about.md) | Architecture overview: components, request lifecycle, key features. |
| [config.md](docs/config.md) | Full reference for every `config.py` key, grouped by purpose. |

⚙️ **Internals**

| Page | What's inside |
|------|---------------|
| [lifespan.md](docs/lifespan.md) | Startup & shutdown: client init, caches, schema, flush loop. |
| [middleware.md](docs/middleware.md) | The request pipeline: token, auth/role checks, rate-limit, cache, logging. |

🚀 **Features**

| Page | What's inside |
|------|---------------|
| [auth.md](docs/auth.md) | Signup, the login methods, JWT tokens, roles, and OTP. |
| [postgres.md](docs/postgres.md) | Primary Postgres pool, named read pools, `db` routing, and connection sizing. |
| [crud.md](docs/crud.md) | Generic CRUD on any table — filters, relations, group-by. |
| [messaging.md](docs/messaging.md) | In-app direct messages and notifications: inbox, threads, read state. |
| [blob.md](docs/blob.md) | File storage over S3 / Azure: upload, presigned URLs, preview, delete. |
| [comms.md](docs/comms.md) | Send email (SES/Resend/Azure) and SMS (SNS/Fast2SMS) via pluggable providers. |
| [admin.md](docs/admin.md) | Admin toolkit: query runners, AI SQL, imports, schema info, cache refresh. |
| [workers.md](docs/workers.md) | Background workers: queue consumers, the worker-status retry pattern. |
| [security.md](docs/security.md) | The layered security model and a production hardening checklist. |

🧱 **Building on Atom**

| Page | What's inside |
|------|---------------|
| [guideline.md](docs/guideline.md) | Step-by-step guide for adding a new API, with a complete example. |
| [router.md](docs/router.md) | How to add an API: naming, param reading, thin routes, responses. |
| [extend.md](docs/extend.md) | Add routes, logic, tables, workers without editing core files. |
| [faq.md](docs/faq.md) | Short answers to common "how do I…" questions. |

## Contributing

Atom is opinionated but built to be extended. For your own project, add features through drop-in `config_extend.py` / `function_extend.py` and new files in `router/` — never edit core files — so you can keep pulling upstream updates with `sync.py`. See [extend.md](docs/extend.md).

Issues and pull requests are welcome at [github.com/atom36942/atom](https://github.com/atom36942/atom).

## License

Released under the [MIT License](LICENSE).
