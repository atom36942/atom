### About 
| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend for rapid large-scale development. |
| **Architecture** | Modular setup with `core/` for framework logic and `function/` for domain logic. |
| **Reliability** | Pure functions within `core/function.py` to minimize side effects. |
| **Production** | Rapidly build APIs, background jobs, and modular integrations. |
| **Efficiency** | Centralized client initialization in `function/client.py`. |
| **Flexibility** | Non-opinionated and fully extensible modular micro-framework. |
| **Tech Stack** | FastAPI, Postgres, Redis, RabbitMQ, Kafka, Celery, S3. |

###  Setup
```bash
# Local Deployment
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/python -V
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
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

# Consumers (Modules)
./venv/bin/python -m core.consumer redis default
./venv/bin/python -m core.consumer rabbitmq default
./venv/bin/python -m core.consumer kafka default
./venv/bin/python -m core.consumer celery default
```

###  FAQ
| Category | Description |
| :--- | :--- |
| **API Master** | Interactive API tester at `static/api.html`. |
| **Postgres Init** | Automatic `func_postgres_init` run on startup. |
| **Access App State** | Global clients (DB, Redis, etc.) via `request.app.state`. |
| **User Context** | Current user state (id, role, etc.) via `request.state.user`. |
| **Manual Auth Check** | Check via `if request.state.user is None: raise Exception("Unauthorized")`. |
| **Admin Control** | Role checks via `user_role_check` in `config_api` (Modes: realtime, token, inmemory, redis). |
| **User Active Check** | Status checks via `user_is_active_check` in `config_api` (Modes: realtime, token, inmemory, redis). |
| **API Caching** | Cache logic via `api_cache_sec` in `config_api` (Modes: inmemory, redis). |
| **API Ratelimiter** | Rate limits via `api_ratelimiting_times_sec` in `config_api` (Modes: inmemory, redis). |
