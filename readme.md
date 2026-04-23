### About 
Atom is a high-performance, modular backend framework designed for rapid development and scalable orchestration.
It provides a robust foundation for building modern APIs and managing background processes with extreme efficiency.
Designed for distributed systems, it offers seamless integration and unified observability for diverse data and messaging ecosystems.
It follows strict architectural standards to ensure high reliability and optimal performance in demanding production environments.

# Setup
```bash
# Local Deployment
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
venv/bin/python -V
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/python main.py
venv/bin/uvicorn main:app --reload

# Docker Deployment
docker build -t atom .
docker run --rm -p 8000:8000 atom

# Sample .env
config_postgres_url="postgresql://atom@127.0.0.1/postgres"
config_redis_url="redis://localhost:6379"
config_rabbitmq_url="amqp://guest:guest@localhost:5672"
config_mongodb_url="mongodb://localhost:27017"

# Consumers
venv/bin/python -m core.consumer redis default
venv/bin/python -m core.consumer rabbitmq default
venv/bin/python -m core.consumer celery default
venv/bin/python -m core.consumer kafka default
```

###  FAQ
| What | Description |
| :--- | :--- |
| **API Master** | Interactive API tester at `static/api/index.html`. |
| **Postgres Init** | Automatic `func_postgres_schema_init` run on startup. |
| **Access App State** | Global clients (DB, Redis, etc.) via `request.app.state`. |
| **User Context** | Current user state (id, role, etc.) via `request.state.user`. |
| **Manual Auth Check** | Check via `if request.state.user is None: raise Exception("Unauthorized")`. |
| **Admin Check** | Role checks via `user_role_check` in `config_api` (Modes: realtime, token, inmemory, redis). |
| **User Active Check** | Status checks via `user_is_active_check` in `config_api` (Modes: realtime, token, inmemory, redis). |
| **API Caching** | Cache logic via `api_cache_sec` in `config_api` (Modes: inmemory, redis). |
| **API Ratelimiter** | Rate limits via `api_ratelimiting_times_sec` in `config_api` (Modes: inmemory, redis). |
| **Postgres Column Control** | Column control keys: `name`, `datatype`, `default`, `index`, `unique`, `is_mandatory`, `regex`, `in`, `check`, `old`. |

