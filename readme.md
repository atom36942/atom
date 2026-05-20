### About
Atom is a high-performance, developer-centric ASGI orchestrator designed for atomic data orchestration and scalable distributed systems.

| Feature | Description |
| :--- | :--- |
| **🚀 ASGI Kernel** | High-density orchestrator for low-latency distributed services. |
| **🧩 Modular Core** | Decoupled architecture with stateless functional logic layer. |
| **🔄 Auto Schema** | Automated PostgreSQL schema synchronization and maintenance. |
| **🌐 Unified IO** | Centralized async clients for Postgres, Redis, Mongo, and S3. |
| **⚙️ Task Engine** | Unified multi-queue dispatching via Celery, Kafka, and RabbitMQ. |
| **🛡️ Auth Guard** | Hardened Argon2id security with built-in RBAC and status checks. |
| **⚡ Smart Cache** | Multi-backend response caching and integrated rate limiting. |
| **🛠️ API Sandbox** | Native interactive tester for real-time endpoint exploration. |
| **📊 Monitoring** | Integrated DB-level API logging and Sentry error tracking. |
| **☁️ Cloud Native** | Out-of-the-box integrations for AWS, Azure, and Google Cloud. |

# Commands
```bash
#Direct Deployment
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

# Test
venv/bin/pytest -s -v

# Consumer Start
venv/bin/python -m core.consumer.<filename> [redis|rabbitmq|kafka|celery]
```

# Env
```bash
config_postgres_url=postgresql://atom@127.0.0.1/postgres?sslmode=disable
config_postgres_url_read=postgresql://app_readonly:123456@127.0.0.1/postgres?sslmode=disable
config_redis_url=redis://localhost:6379
config_mongodb_url=mongodb://localhost:27017
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_celery_url=redis://localhost:6379
config_redis_queue_url=redis://localhost:6379
config_root_user_password="your-secure-password"
config_token_secret_key="your-secure-token-secret-key-here"
config_is_enable_signup=0
config_is_enable_postgres_sql_runner_write=0
config_is_enable_traceback=0
```
