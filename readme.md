# Atom
Batteries-included FastAPI framework for production backends: auth, CRUD over any table, caching, rate limits, queues, workers, web pages and optional integrations, all driven by config. Your code lives in `*_extend` paths, so updating Atom never overwrites it.

Details: [docs/about.md](docs/about.md)

# Installation
```bash
# 1. Python 3.14, once (macOS; on Linux: sudo apt install python3.14 or sudo dnf install python3.14)
brew update
brew install python@3.14
python3.14 --version
python3 --version

# 2. new project with sync.py
mkdir <project>
cd <project>
git init
curl -fsSL -o sync.py https://raw.githubusercontent.com/atom36942/atom/main/sync.py
python3 sync.py

# 3. run, then open http://localhost:8000
venv/bin/python main.py
venv/bin/uvicorn main:app --reload
```

Windows: [docs/windows.md](docs/windows.md)

# Env
```env
config_postgres_url_master=postgresql://postgres:postgres@localhost:5432/postgres
config_root_user_password=your-strong-root-password
config_token_secret_key=your-secret-key-at-least-32-chars
config_signup_allowed_roles=[2]
config_is_prod=false
config_is_pgweb_enabled=true
config_redis_url_api_response=redis://localhost:6379/0
```

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

# Sync
Commit your work and stop the app first.
```bash
python3 sync.py                              # update files, rebuild venv/, list newer # extend packages
python3 sync.py --no-outdated                # same, without the PyPI lookup
python3 sync.py --no-venv                    # files only
python3 sync.py --no-venv --no-outdated      # CI
python3 sync.py --status                     # Atom version of this project and the latest
```

Details: [docs/sync.md](docs/sync.md)

# Test
```bash
venv/bin/ruff check .
venv/bin/python -m unittest discover -s tests_extend -t .
```

# Contributing
To work on Atom itself:
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3.14 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/ruff check .
venv/bin/python -m unittest discover -s tests -t .
```

Then open a pull request against `main`. Details: [tests/README.md](tests/README.md)

# Docs
- **Start:** [quickstart](docs/quickstart.md) · [about](docs/about.md) · [config](docs/config.md) · [extend](docs/extend.md) · [sync](docs/sync.md) · [windows](docs/windows.md) · [faq](docs/faq.md) · [AGENTS.md](AGENTS.md)
- **Features:** [auth](docs/auth.md) · [crud](docs/crud.md) · [ownership](docs/ownership.md) · [database](docs/database.md) · [redis](docs/redis.md) · [queue](docs/queue.md) · [messaging](docs/messaging.md) · [storage](docs/storage.md)
- **Operate:** [admin](docs/admin.md) · [performance](docs/performance.md) · [security](docs/security.md) · [audit](docs/audit.md) · [tests](tests/README.md)

# License
MIT.
