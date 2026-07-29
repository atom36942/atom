# Atom

**Batteries-included, opinionated FastAPI framework for shipping production backends fast.**

Atom gives you authentication, generic CRUD over any table, caching, rate-limiting, background workers, blob storage, and a dozen pluggable integrations (Postgres, Redis, Mongo, S3/Azure, Kafka/RabbitMQ/Celery, OpenAI/Gemini) out of the box — while staying fully extensible, so you keep complete freedom to add your own logic. Every integration is optional (it activates only when its config is set), behavior is driven by data in `config.py`, and you extend the framework via drop-in modules so updates never clobber your code.

## Highlights

- 🔐 **Auth built in** — JWT tokens, signup/login by password, email/mobile OTP, or Google; role-based access.
- 🗃️ **Generic CRUD** — create/read/update/delete any table with filters, relations, and pagination — no per-table code.
- ⚡ **Fast by default** — per-endpoint response caching, rate-limiting, and buffered writes off the hot path.
- 🧩 **Pluggable everything** — swap Postgres/Redis/Mongo/S3/Azure/Kafka/RabbitMQ/Celery/OpenAI/Gemini by setting config.
- 🛠️ **Admin toolkit** — SQL query runners, AI-generated SQL, data imports, schema introspection.
- 📦 **Background workers** — queue consumers and a durable retry pattern using just Postgres.
- 🧾 **Self-documenting** — OpenAPI spec + a built-in API console at `/`.
- 🔧 **Extend without forking** — drop-in `config_extend.py` / `function_extend.py`; pull updates with `sync.py`.

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
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

<details>
<summary><b>macOS + Homebrew (pinned Python)</b></summary>

Using a specific Homebrew Python and starting from a clean venv:

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
</details>

### Run

Development (auto-reload):

```bash
venv/bin/uvicorn main:app --reload
```

Directly with Python (reads `PORT`, defaults to 8000):

```bash
venv/bin/python main.py
```

The server starts on **http://localhost:8000**. Useful endpoints:

- `/` — built-in API console (served HTML)
- `/health` — health check
- `/info` — live API list, DB schema, and config
- `/openapi.json` — generated OpenAPI spec

### Docker

```bash
docker build -t atom .
docker run --rm -p 8000:8000 --env-file .env atom
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
   config_postgres_url_read=postgresql://user_read:123456@127.0.0.1:5432/postgres?sslmode=disable
   config_redis_url=redis://localhost:6379
   config_redis_url_queue=redis://localhost:6379
   config_mongodb_url=mongodb://localhost:27017
   config_rabbitmq_url=amqp://guest:guest@localhost:5672
   config_celery_url=redis://localhost:6379
   ```

   `.env` is git-ignored — keep your secrets there. Only set what you need; unset integrations stay dormant.

2. **`config_extend.py`** — a git-ignored, drop-in module for overriding or adding any config value in code. Add `function_extend.py` the same way to override or extend logic. Both are auto-loaded if present, so framework updates via `sync.py` never clobber your customizations.

See [config.md](docs/config.md) for a full, grouped reference of every config key.

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
venv/bin/python script/consumer_postgres_create.py
venv/bin/python script/worker_resume_parser.py
```

These rely on a configured queue backend (`config_redis_url_queue`, `config_rabbitmq_url`, `config_kafka_url`, or `config_celery_url`). See [workers.md](docs/workers.md).

## Updating Atom

`sync.py` pulls the latest framework files from upstream while leaving your `.env`, `config_extend.py`, and `function_extend.py` untouched:

```bash
venv/bin/python sync.py
```

It fetches `main`, then checks out the core files (`main.py`, `function.py`, `config.py`, routers, `static/api.html`, `Dockerfile`, etc.). `requirements.txt` is only pulled if you don't already have one — re-run the install step afterward if it changes.

## Documentation

**Getting started**
- [about.md](docs/about.md) — Architecture overview: components, request lifecycle, and key features.
- [config.md](docs/config.md) — Full reference for every `config.py` key, grouped by purpose.

**Internals**
- [lifespan.md](docs/lifespan.md) — Startup & shutdown internals: client init, caches, schema, flush loop.
- [middleware.md](docs/middleware.md) — The request pipeline: token, auth/role checks, rate-limit, cache, logging.

**Features**
- [auth.md](docs/auth.md) — Authentication: signup, the login methods, JWT tokens, roles, and OTP.
- [crud.md](docs/crud.md) — Generic CRUD: create/read/update/delete any table, filters, relations, group-by.
- [messaging.md](docs/messaging.md) — In-app direct messages and notifications: inbox, threads, read state.
- [blob.md](docs/blob.md) — File storage over S3 / Azure: upload, presigned URLs, preview, delete.
- [comms.md](docs/comms.md) — Send email (SES/Resend/Azure) and SMS (SNS/Fast2SMS) via pluggable providers.
- [admin.md](docs/admin.md) — Admin toolkit: query runners, AI SQL, imports, schema info, cache refresh.
- [workers.md](docs/workers.md) — Background workers: queue consumers, the worker-status retry pattern, cleanup jobs.
- [security.md](docs/security.md) — The layered security model and a production hardening checklist.

**Building on Atom**
- [router.md](docs/router.md) — How to add an API: naming, param reading, thin routes, and response structure.
- [extend.md](docs/extend.md) — Add routes, logic, tables, and workers without editing core files; updating via `sync.py`.

**Help**
- [faq.md](docs/faq.md) — Short answers to common "how do I…" questions.

## Contributing

Atom is opinionated but built to be extended. For your own project, add features through drop-in `config_extend.py` / `function_extend.py` and new files in `router/` — never edit core files — so you can keep pulling upstream updates with `sync.py`. See [extend.md](docs/extend.md).

Issues and pull requests are welcome at [github.com/atom36942/atom](https://github.com/atom36942/atom).

## License

Released under the [MIT License](LICENSE).
