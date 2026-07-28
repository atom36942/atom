# Documentation

**Getting started**
- [about.md](docs/about.md) — Architecture overview: components, request lifecycle, and key features.
- [setup.md](docs/setup.md) — Install, configure, run (local & Docker), workers, and the secrets to override.
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
