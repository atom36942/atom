# Atom

[![Release](https://img.shields.io/github/v/release/atom36942/atom?label=release&sort=semver)](https://github.com/atom36942/atom/releases) [![tests](https://github.com/atom36942/atom/actions/workflows/tests.yml/badge.svg)](https://github.com/atom36942/atom/actions/workflows/tests.yml) ![Python 3.14](https://img.shields.io/badge/python-3.14-blue) [![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/atom36942/atom/blob/main/LICENSE)

Batteries-included FastAPI framework for production backends: auth, CRUD over any table, caching, rate limits, queues, workers, web pages and optional integrations, all driven by config. Your code lives in `*_extend` paths, so updating Atom never overwrites it.

Details: [docs/about.md](docs/about.md) · Changelog: [CHANGELOG.md](CHANGELOG.md)

# Installation (new project)
```bash
# 1. Python 3.14 (once; Linux: apt or dnf install python3.14)
brew update
brew install python@3.14
python3.14 --version
python3 --version

# 2. project
mkdir <project>
cd <project>
git init
curl -fsSL -o sync.py https://raw.githubusercontent.com/atom36942/atom/main/sync.py
python3 sync.py                                 # Atom files and venv

# 3. run (http://localhost:8000)
venv/bin/python main.py                         # default
venv/bin/uvicorn main:app --reload              # restart on file change
PORT=8001 venv/bin/python main.py               # another port
venv/bin/uvicorn main:app --reload --port 8001  # another port, restart on file change
```

Windows: [docs/windows.md](docs/windows.md)

# Env
Atom starts without `.env`: pages, `/health` and routes that don't use the database work.

Required for the database, users and login:
```env
config_postgres_url_master=postgresql://postgres:postgres@localhost:5432/postgres
config_root_user_password=your-strong-root-password
config_token_secret_key=your-secret-key-at-least-32-chars
```

Optional:
```env
config_is_pgweb_enabled=true
config_is_prod=false
config_is_log_api=false
config_cors_allow_origins=["http://localhost:5173"]
config_redis_url_api_response=redis://localhost:6379/0
config_redis_url_user_state=redis://localhost:6379/0
config_redis_url_ratelimiter=redis://localhost:6379/0
config_redis_url_queue=redis://localhost:6379/0
```

Keep `.env` to secrets and per-environment values; settings that are the same everywhere (`config_root_html_path`, `config_signup_allowed_roles`) usually go in `config_extend.py`.

Layout: `# atom` (Atom's keys), `# extend` (the project's keys), then `# script.<name>` listing every key one script reads, all commented out until a developer runs that script.

Details: [docs/config.md](docs/config.md)

# Extend
Atom owns every unsuffixed path; you own the `*_extend` ones.

| What | Where |
|---|---|
| Settings, tables, route rules | `config_extend.py` |
| API routes | `router_extend/<feature>.py` |
| Logic (`func_*`) | `function_extend/<feature>.py` |
| Constants, param specs, templates | `files_extend/` |
| Web pages | `static_extend/<name>.html` or `static_extend/<name>/index.html` |
| Scripts and workers | `script_extend/<name>.py` |
| Tests | `tests_extend/test_<feature>.py` |
| Docs | `docs_extend/<feature>.md` |
| Packages | `requirements.txt` under `# extend`, pinned `==` |

Details: [docs/extend.md](docs/extend.md)

# Update (bring a project to the latest Atom)
Every project on Atom shares most of its code and the same rules, so any developer can open any project and know where things are. Updating takes two steps, run from time to time (after an Atom release, or monthly):

| Step | Covers | What it does | Run |
| :--- | :--- | :--- | :--- |
| 1. Sync | about 90%: Atom's core | Replaces Atom's own files (`function/`, `router/`, `static/`, `docs/`, `config.py`, `AGENTS.md`, ...) with the latest version, exactly; the project's code is never touched | `python3 sync.py` |
| 2. Rules | about 5%: the shared standard | The AI agent brings the project's own code in line with `AGENTS.md`: structure, security, speed and scale, the page flow (login, account menu, sync, settings), clean-up; it proposes first and fixes after your OK | the prompt below |
| (yours) | the rest | The project's own features and screens: nothing changes them | — |

Step 2 prompt (sync prints it too):
```text
Update this repo to the latest Atom: follow Update in AGENTS.md.
```

## Sync options
Commit your work and stop the app first.
```bash
python3 sync.py                              # update files, rebuild venv/, list newer # extend packages
python3 sync.py --no-outdated                # same, without the PyPI lookup
python3 sync.py --no-venv                    # files only
python3 sync.py --no-venv --no-outdated      # CI
python3 sync.py --status                     # Atom version of this project and the latest
```

Details: [docs/sync.md](docs/sync.md)

# Check (startup, ruff, pages, tests)
```bash
venv/bin/python -m script.check
```
Runs the startup checks, ruff, a check that every `app_state.func_*` the project calls still exists, the pages' JavaScript and the tests in `tests_extend/` together and prints one summary line, plus only the failures.

# Other ways to start
## Existing project (built on Atom)
```bash
git clone <repo-url>
cd <project>
python3 sync.py                                 # Atom files and venv
venv/bin/python main.py                         # run
```

## Contributing (change Atom itself)
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3.14 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
docker compose up -d                            # optional: local Postgres (PostGIS), Redis, RabbitMQ
venv/bin/python -m script.check                 # must pass before a pull request
```

Then open a pull request against `main`. Details: [CONTRIBUTING.md](https://github.com/atom36942/atom/blob/main/CONTRIBUTING.md) · [Code of Conduct](https://github.com/atom36942/atom/blob/main/CODE_OF_CONDUCT.md) · [tests/README.md](tests/README.md)

# Docs
| Area | Doc | About |
|---|---|---|
| Start | [quickstart](docs/quickstart.md) | Run Atom, sign up, log in and write your first records |
|  | [about](docs/about.md) | Why Atom is built this way, and where each file lives |
|  | [config](docs/config.md) | Every setting in config.py and .env, with its default |
|  | [extend](docs/extend.md) | Where a project's own routes, tables, pages and code go |
|  | [sync](docs/sync.md) | Updating a project to a new Atom, pinning, rolling back |
|  | [windows](docs/windows.md) | Running Atom and its scripts on Windows |
|  | [faq](docs/faq.md) | Common questions and quick answers |
|  | [AGENTS.md](AGENTS.md) | Rules every project and AI agent follows, and Update |
| Auth | [auth](docs/auth.md) | Users, roles, every login method, tokens, password reset |
|  | [auth-permission](docs/auth-permission.md) | Give selected users create, read, update, delete per table |
|  | [auth-api-key](docs/auth-api-key.md) | API keys for other systems, scoped and revocable |
|  | [auth-totp](docs/auth-totp.md) | Two-factor login with an authenticator app (TOTP) |
|  | [auth-oidc](docs/auth-oidc.md) | Sign in with Google, Microsoft or any OIDC provider |
|  | [user-management](docs/user-management.md) | Add, edit, deactivate and invite an app's users |
| Data | [crud](docs/crud.md) | Create, read, update, delete any table: filters, paging |
|  | [crud-search](docs/crud-search.md) | Search words in text, ranked by relevance (Postgres) |
|  | [crud-vector](docs/crud-vector.md) | Find rows by meaning with AI embeddings (pgvector) |
|  | [ownership](docs/ownership.md) | Users read and change only the rows they own |
|  | [database](docs/database.md) | Connections, tables from config, AI questions in plain words |
|  | [timescaledb](docs/timescaledb.md) | Time-series data with TimescaleDB |
|  | [storage](docs/storage.md) | Upload and serve files in S3 or Azure Blob |
| Jobs | [queue](docs/queue.md) | Background jobs on Postgres, or Redis, RabbitMQ, Kafka, Celery |
|  | [schedule](docs/schedule.md) | Run scripts on a schedule |
|  | [webhook](docs/webhook.md) | Send signed webhooks out, verify the ones coming in |
|  | [messaging](docs/messaging.md) | In-app messages and chat, email and SMS |
|  | [redis](docs/redis.md) | Cache, rate limits and shared state in Redis |
| Build | [backend](docs/backend.md) | How to write routes, functions and SQL the Atom way |
|  | [frontend](docs/frontend.md) | Pages: login flow, lists, storage, export |
| Operate | [admin](docs/admin.md) | Built-in pages (database, monitor, API), admin APIs |
|  | [performance](docs/performance.md) | Tuning, indexes and profiling slow routes |
|  | [benchmark](docs/benchmark.md) | Measured requests per second and latency |
|  | [security](docs/security.md) | How each request is checked, and what is protected |
|  | [audit](docs/audit.md) | Security audit: findings and fixes |
|  | [tests](tests/README.md) | Running the unit and integration tests |

Showcase for everyone: `/page/atom` on any Atom app.

# License
MIT.
