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
```


## FAQ

### API Master & Static Assets
- **API Master**: Access the interactive API tester at `static/api.html`.
- **Static Content**: All files in the `static/` directory are served automatically via the `/static/` prefix.

### Postgres Database
- **Auto Initialization**: The system automatically runs `func_postgres_init` on application startup.
- **Manual Sync**: Perform a full system refresh or schema update via the `/admin/sync` API.
- **Configuration**: All schema, table, and data control settings are managed via `config_postgres` in `config.py`.
- **Deletion Protection**: 
  - **Single Row**: Use `table_row_delete_disable` (e.g., `["*"]` for all or `["users"]` for specific tables).
  - **Bulk Deletion**: Use `table_row_delete_disable_bulk` (e.g., `[["*", 1000]]` or `[["users", 1]]`).

### App & User State
- **Access App State**: Access global clients (DB, Redis, etc.) and configuration singletons via `request.app.state`.
- **User Context**: Access the current authorized user's state (id, role, etc.) via `request.state.user`.
- **Dynamic Profile Keys**: Use the `profile_metadata` field in `config_sql` to define dynamic, SQL-based profile keys.

### API Policies
- **Access Control**: Roles are managed via `user_role_check` in `config_api`. Available modes: `realtime`, `inmemory`, `token`, `redis`.
- **User Status Check**: Enforce active status via `user_is_active_check` in `config_api`.
- **Caching**: Configure response caching using `api_cache_sec` in `config_api`.
- **Rate Limiting**: Set limits using `api_ratelimiting_times_sec" in `config_api`.

### Auth Patterns
- **Manual Auth Check**: Use `if request.state.user is None: raise Exception("Unauthorized")` within your functional logic.
- **Route Prefixes**:
  - `index/` (or `/`): Public system metadata, health checks, and landing pages.
  - `auth/`: Endpoints for signing up, logging in, and OTP verification.
  - `my/`: User-restricted actions. Access is automatically scoped to `request.state.user["id"]`.
  - `public/`: Data accessible without an authentication token (subject to `config_api` overrides).
  - `private/`: General authenticated access (any valid token).
  - `admin/`: Management-level routes restricted to administrative roles.

### Extending the Router
The Atom Framework uses **Dynamic Router Discovery**. To add new endpoints:
1. Create a new `.py` file within the `router/` directory (e.g., `router/custom.py`).
2. Define an `APIRouter` instance named `router`.
3. Add your endpoints to this instance.
The system will automatically discover and include these routes on the next startup.

### Consumers

The background worker system uses a minimalist, top-down linear architecture for maximum performance and surgical execution. Start a worker by specifying the technology and the target channel:

```bash
# General Signature: ./venv/bin/python consumer.py [tech] [channel]
./venv/bin/python consumer.py redis default
./venv/bin/python consumer.py rabbitmq default
./venv/bin/python consumer.py kafka default
./venv/bin/python consumer.py celery default
```

The infrastructure is built on **Dynamic Task Discovery**, requiring zero configuration to add new workers:
- **Add a Task**: Simply define an `async` function in `function.py`.
- **Resource Aware**: If your task needs the database, ensure it accepts `postgres_pool`. The consumer will intelligently inject the pool only if your signature requests it.
- **Trigger**: Tasks are queued using the `tech_channel` format (e.g., `redis_default`).

```python
# Create a task object and dispatch via the universal producer logic
task_obj = {"task_name": "func_your_custom_function", "params": {"id": 123}}
await func_producer_logic("redis_your_channel", task_obj, producer_obj)
```

