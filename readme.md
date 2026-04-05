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
| :--- | :--- | :--- |
| 1 | **API Master** | Interactive tester at `static/api.html` or `/page-api` |
| 2 | **Serve static content** | Served via the `static/` directory prefix. |
| 3 | **Serve html pages** | `/page-{name}` or `/s/{name}` for `static/` HTML files. |
| 4 | **Database Init Auto** | Runs `func_postgres_init` on startup. |
| 5 | **Database Manual Init** | Full system refresh via `/admin/sync` API. |
| 6 | **Access App State** | Global clients and config singletons via `request.app.state`. |
| 7 | **Access Request User State** | Authorized user context (id, role, etc.) via `request.state.user`. |
| 8 | **Database Schema Change** | Use `config_postgres` in `config.py`. |
| 9 | **Override config.py** | Add the same key with your value in the `.env` file. |
| 10 | **User Profile Keys** | Use `profile_metadata` in `config_sql` for dynamic SQL-based keys. |
| 11 | **Admin API Access** | Use `user_role_check: ["mode", [roles]]` in `config_api` (e.g. `["realtime", [1,2,3]]`). |
| 12 | **User Active Check** | Use `user_is_active_check: ["mode", 1]` in `config_api` (1=Enable, 0=Disable). |
| 13 | **API Caching** | Use `api_cache_sec: ["mode", seconds]` in `config_api` (e.g. `["inmemory", 60]`). |
| 14 | **API Rate Limiting** | Use `api_ratelimiting_times_sec: ["mode", count, seconds]` in `config_api`. |
| 15 | **Column Index** | Use `index: "btree"` (or `gin`/`gist`) in `config_postgres` column. |
| 16 | **Mandatory Column** | Use `is_mandatory: 1` in `config_postgres` column definition. |
| 17 | **Enum (IN) Column** | Use `in: (val1, val2)` in `config_postgres` column to restrict values. |
| 18 | **Match Columns** | Use `is_match_column: 1` in `control` to enforce exact schema matching. |
| 19 | **Disable Drop Table** | Use `is_drop_disable_table: 1` in `control` to prevent table deletion. |
| 20 | **Disable Truncate** | Use `is_truncate_disable: 1` in `control` to prevent table truncation. |
| 21 | **Unique Constraint** | Use `unique: "col1,col2"` in `config_postgres` for unique keys. |
| 22 | **Regex Validation** | Use `regex: "pattern"` in `config_postgres` column definition. |
| 23 | **Rename Column** | Use `old: "old_name"` in `config_postgres` column mapping. |
| 24 | **Soft Delete Children** | Use `is_child_delete_soft: 1` in `control` to soft-delete related records. |
| 25 | **Hard Delete Children** | Use `is_child_delete_hard: 1` in `control` to hard-delete related records. |
| 26 | **Disable Role Delete** | Use `is_delete_disable_role: 1` in `control` to restrict deletions. |
| 27 | **Disable Bulk Delete** | Use `delete_disable_bulk: [["table", role]]` in `control` for bulk delete. |
| 28 | **Disable Table Delete** | Use `delete_disable_table: ["users"]` in `control` for specific tables. |
| 29 | **Manual Auth Check** | Use `if request.state.user is None: raise Exception("Unauthorized")` in logic. |
