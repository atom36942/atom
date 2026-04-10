### About 
| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend for rapid large-scale development. |
| **Architecture** | Modular setup combining functional and procedural styles. |
| **Reliability** | Pure functions to minimize side effects and improve testing. |
| **Production** | Rapidly build APIs, background jobs, and integrations. |
| **Efficiency** | Minimal boilerplate to avoid reinventing the wheel. |
| **Flexibility** | Non-opinionated and fully extensible framework. |
| **Tech Stack** | FastAPI, Postgres, Redis, RabbitMQ, Kafka, Celery, S3. |

###  Setup
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

#Consumers
./venv/bin/python consumer.py redis default
./venv/bin/python consumer.py rabbitmq default
./venv/bin/python consumer.py kafka default
./venv/bin/python consumer.py celery default
```
---

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
