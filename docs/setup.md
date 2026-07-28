# Setup

How to install, configure, run, and update Atom.

## Requirements

- **Python 3.11+** (Docker image uses 3.11; the venv flow works on newer versions too)
- **Git**
- For MSSQL support: the **unixODBC** system libraries (`unixodbc unixodbc-dev`) — already installed in the Docker image
- Optional services you plan to enable: Postgres, Redis, MongoDB, etc.

Atom needs **no service to boot** — every integration is optional. A bare clone runs; features light up as you add config.

## Local Installation

```bash
git clone https://github.com/atom36942/atom.git
cd atom

python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

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

### Common config keys

| Key | Purpose |
|-----|---------|
| `config_postgres_url` / `_read` / `_external` | Primary, read-replica, and external Postgres pools |
| `config_redis_url` / `config_redis_url_queue` | Cache/rate-limit store and background-job queue |
| `config_mongodb_url` | MongoDB connection |
| `config_mssql_url` / `_read` | MSSQL pools |
| `config_token_secret_key` | JWT signing secret — **change this in production** |
| `config_root_user_password` | Seeded root user password — **change this** |
| `config_openai_key` / `config_gemini_key` | AI features (e.g. query generation) |
| `config_aws_*` / `config_azure_*` | S3/SNS/SES and Azure Blob/Email |
| `config_is_enable_signup` | Toggle public signup |
| `config_is_debug` | Debug mode |

See [config.md](config.md) for a full, grouped reference of every config key and how it's used.

## Running

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

## Docker

```bash
docker build -t atom .
docker run --rm -p 8000:8000 --env-file .env atom
```

The image installs ODBC drivers and all dependencies, then runs `python main.py` on port 8000.

## Background Workers

Standalone processes in `script/` run outside the API — start them as separate processes when you need queue consumers or batch jobs:

```bash
venv/bin/python script/consumer_postgres_create.py
venv/bin/python script/worker_resume_parser.py
```

These rely on a configured queue backend (`config_redis_url_queue`, `config_rabbitmq_url`, `config_kafka_url`, or `config_celery_url`).

## Updating Atom

`sync.py` pulls the latest framework files from upstream while leaving your `.env`, `config_extend.py`, and `function_extend.py` untouched:

```bash
venv/bin/python sync.py
```

It fetches `main`, then checks out the core files (`main.py`, `function.py`, `config.py`, routers, `static/api.html`, `Dockerfile`, etc.). `requirements.txt` is only pulled if you don't already have one — re-run the install step afterward if it changes.

## Next Steps

See [about.md](about.md) for the architecture and how to extend Atom with your own routes and logic.
