# ⚛️ Atom

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)

**Batteries-included FastAPI framework for production backends.** Auth, generic CRUD over any table, caching, rate limiting, queues, workers, blob storage and optional integrations (Postgres, Redis, Mongo, SQL Server, ClickHouse, S3, Azure, Kafka, RabbitMQ, Celery, OpenAI, Gemini, Sentry, PostHog), all driven by config. Your code lives in `*_extend` paths, so updating Atom never overwrites it.

## Features
- **Auth:** JWT, password / OTP / Google login, roles, per-route checks in `config_api`.
- **CRUD:** create, read, update, delete any table with filters, relations, pagination and ownership.
- **Speed:** per-route response cache, rate limits, buffered writes.
- **Jobs:** queue consumers and durable retry workers.
- **Admin tools:** SQL runner, data import, schema browser, memory report.
- **Web pages:** every page in `static/` and `static_extend/` opens at `/page/<name>` and is listed at `/`.

## Install
Needs Python 3.14 (the `Dockerfile` version) and Git.

**macOS / Linux:**
```bash
brew install python@3.14                     # macOS; on Linux install python3.14 from your distribution
git clone https://github.com/atom36942/atom.git <project>
cd <project>
python3.14 -m venv venv
venv/bin/pip install -r requirements.txt
```

**Windows (PowerShell; Python 3.14 from python.org):**
```powershell
git clone https://github.com/atom36942/atom.git <project>
cd <project>
py -3.14 -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## Run
```bash
venv/bin/python main.py                      # Atom's server settings (workers, PORT, startup checks)
venv/bin/uvicorn main:app --reload           # or: restart on code changes while developing
```
On Windows use `venv\Scripts\python main.py`. Open http://localhost:8000: `/` lists the apps, `/page/api` is the API console, `/health`, `/openapi.json`. Start Atom from its own folder (`.env`, `static/`, `tmp/` are read from there).

Docker: `docker build -t atom .` then `docker run --rm -p 8000:8000 --env-file .env atom`.

## Configure
Defaults are in `config.py`. Override them in `config_extend.py` (project settings, tables, routes) or `.env` (secrets, URLs; wins over both).
```env
config_postgres_url_master=postgresql://postgres:postgres@localhost:5432/postgres
config_root_user_password="your-strong-root-password"
config_token_secret_key="your-secret-key-at-least-32-chars"
```
Before deploying, follow the [production checklist](docs/security.md#5-production-hardening-checklist).

## Extend
Atom owns every unsuffixed path; you own the `*_extend` ones.

| What | Where |
|---|---|
| Settings, tables, route rules | `config_extend.py` |
| API routes | `router_extend/<feature>.py` |
| Logic (`func_*`) | `function_extend/<feature>.py` |
| Constants, param specs, templates | `files_extend/` |
| Web pages (open at `/page/<name>`) | `static_extend/<name>.html` or `static_extend/<name>/index.html` |
| Scripts and workers (one self-contained file each) | `script_extend/<name>.py` |
| Tests, docs | `tests_extend/`, `docs_extend/` |
| Packages | `requirements.txt` under `# extend`, pinned `==` |

Full guide with a working example: [docs/extend.md](docs/extend.md). Rules for AI agents: [AGENTS.md](AGENTS.md).

## Sync
Updates Atom's files, keeps your `*_extend` paths, `config_extend.py` and `.env`, and rebuilds `venv/` to match `requirements.txt`. Commit your work and stop the app first.

**macOS / Linux:**
```bash
# option 1: update files and rebuild venv/
python3 sync.py

# option 2: update files only (--no-venv), then install packages yourself
python3 sync.py --no-venv
venv/bin/pip install -r requirements.txt
```

**Windows (new PowerShell window, outside the venv: run `deactivate` first):**
```powershell
# option 1: update files and rebuild venv\
py sync.py

# option 2: update files only (--no-venv), then install packages yourself
py sync.py --no-venv
venv\Scripts\pip install -r requirements.txt
```

Keep the project out of OneDrive or Dropbox; their file syncing locks files in `venv/`. Details and recovery: [docs/sync.md](docs/sync.md).

## Check
```bash
venv/bin/ruff check .                                   # lint
venv/bin/python -m unittest discover -s tests -t .      # Atom's tests (yours: -s tests_extend)
```

## Docs
- **Start:** [quickstart](docs/quickstart.md) · [about](docs/about.md) · [config](docs/config.md) · [extend](docs/extend.md) · [sync](docs/sync.md) · [faq](docs/faq.md)
- **Features:** [auth](docs/auth.md) · [crud](docs/crud.md) · [ownership](docs/ownership.md) · [database](docs/database.md) · [redis](docs/redis.md) · [queue](docs/queue.md) · [messaging](docs/messaging.md) · [storage](docs/storage.md)
- **Operate:** [admin](docs/admin.md) · [performance](docs/performance.md) · [security](docs/security.md) · [audit](docs/audit.md) · [tests](tests/README.md)

## License
MIT.
