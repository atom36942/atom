# Documentation

- [about.md](docs/about.md) — Architecture overview: components, request lifecycle, and key features.
- [lifespan.md](docs/lifespan.md) — Startup & shutdown internals: client init, caches, schema, flush loop.
- [middleware.md](docs/middleware.md) — The request pipeline: token, auth/role checks, rate-limit, cache, logging.
- [setup.md](docs/setup.md) — Install, configure, run (local & Docker), workers, and the secrets to override.
- [config.md](docs/config.md) — Full reference for every `config.py` key, grouped by purpose.
- [extend.md](docs/extend.md) — Add routes, logic, tables, and workers without editing core files; updating via `sync.py`.

# Deployment
```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.14 -m venv venv
./venv/bin/python --version
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/python main.py
venv/bin/uvicorn main:app --reload
```

# Sample Env
```bash
config_postgres_url=postgresql://atom:123456@127.0.0.1:5432/postgres?sslmode=disable
config_postgres_url_read=postgresql://user_read:123456@127.0.0.1:5432/postgres?sslmode=disable
config_redis_url=redis://localhost:6379
config_mongodb_url=mongodb://localhost:27017
config_redis_url_queue=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_celery_url=redis://localhost:6379
```
