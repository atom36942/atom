## About Us

| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend for rapid large-scale development. |
| **Architecture** | Modular setup combining functional and procedural styles. |
| **Reliability** | Pure functions to minimize side effects and improve testing. |
| **Production** | Rapidly build APIs, background jobs, and integrations. |
| **Efficiency** | Minimal boilerplate to avoid reinventing the wheel. |
| **Flexibility** | Non-opinionated and fully extensible framework. |
| **Tech Stack** | FastAPI, Postgres, Redis, RabbitMQ, Kafka, Celery, S3. |

## Setup
```bash
# Local Deployment
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -V
./venv/bin/python main.py
./venv/bin/uvicorn main:app --reload

# Docker Deployment
docker build -t atom .
docker run --rm -p 8000:8000 atom

# Sample .env
config_postgres="postgresql://atom@127.0.0.1/postgres"
config_redis_url="redis://localhost:6379"
config_rabbitmq_url="amqp://guest:guest@localhost:5672"
config_mongodb_uri="mongodb://localhost:27017"

# Consumers
/venv/bin/python consumer.py redis
./venv/bin/python consumer.py celery
./venv/bin/python consumer.py rabbitmq
./venv/bin/python consumer.py kafka
```

## FAQ

| # | Scenario | Description |
| :---| :--- | :--- |
| 1 | **API Master** | Interactive tester at `static/api.html` or `/page-api` |
| 2 | **Serve static content** | Served via the `static/` directory prefix. |
| 3 | **Serve html pages** | `/page-{name}` or `/s/{name}` for `static/` HTML files. |
| 4 | **PostgreSQL Init Auto** | Runs `func_postgres_init` on startup. |
| 5 | **PostgreSQL Init Manual** | Full system refresh via `/admin/sync` API. |
| 6 | **PostgreSQL Config** | Check `config_postgres` in `config.py` for all schema and control settings. |
| 7 | **User Profile Keys** | Use `profile_metadata` in `config_sql` for dynamic SQL-based keys. |
| 8 | **Access App State** | Global clients and config singletons via `request.app.state`. |
| 9 | **Access Request User State** | Authorized user context (id, role, etc.) via `request.state.user`. |
| 10 | **Override config.py** | Add the same key with your value in the `.env` file. |
| 11 | **Admin API Access** | Use `user_role_check: ["mode", [roles]]` in `config_api`. Modes: `realtime`, `inmemory`, `token`, `redis`. |
| 12 | **User Active Check** | Use `user_is_active_check: ["mode", 1]` in `config_api` (1=Enable, 0=Disable). Modes: `realtime`, `inmemory`, `token`, `redis`. |
| 13 | **API Caching** | Use `api_cache_sec: ["mode", seconds]` in `config_api`. Modes: `inmemory`, `redis`. |
| 14 | **API Rate Limiting** | Use `api_ratelimiting_times_sec: ["mode", count, seconds]` in `config_api`. Modes: `inmemory`, `redis`. |
| 15 | **Manual Auth Check** | Use `if request.state.user is None: raise Exception("Unauthorized")` in logic. |
| 16 | **Postgres Table Delete disable** | Use `table_row_delete_disable: ["*"]` (all) or `["users"]` (specific) in `config_postgres["control"]`. |
| 17 | **Postgres Bulk Delete disable** | Use `table_row_delete_disable_bulk: [["*", 1000]]` (all) or `[["users", 1]]` (specific) in `config_postgres["control"]`. |


