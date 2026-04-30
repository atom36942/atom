### About
Atom is a high-performance, modular backend framework designed for atomic data orchestration and scalable distributed systems.

| Major Feature | Description |
| :--- | :--- |
| **🚀 High Performance** | Low-latency backend orchestration for complex distributed systems. |
| **🧩 Modular Design** | Decoupled architecture with clear separation of core and service layers. |
| **🏗️ SOLID Principles** | Stateless functional logic layer following strict architectural standards. |
| **⚙️ Multi-Queue Engine** | Unified task dispatching via Celery, Kafka, RabbitMQ, or Redis. |
| **🗄️ Schema Sync** | Automatic PostgreSQL schema synchronization and maintenance on startup. |
| **⚡ Smart Routing** | Integrated parameter extraction, validation, and multi-backend caching. |
| **🛡️ Argon2id Security** | Hardened authentication with built-in RBAC and account status checks. |
| **🚀 Stage & Cast** | High-performance bulk ingestion with support for complex data types. |
| **🧩 CRUD Orchestrator** | Role-based object management with owner validation and OTP security. |
| **🛠️ API Sandbox** | Native interactive tester for real-time endpoint exploration and validation. |
| **🌐 Unified Clients** | Centralized dependency injection for Postgres, Redis, MongoDB, and S3. |
| **📊 Observability** | Integrated Prometheus monitoring, Sentry error tracking, and logging. |
| **☁️ Cloud Native** | Out-of-the-box integrations for AWS S3, Jira, GSheet, and Email services. |

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
```

###  FAQ
| What | Description |
| :--- | :--- |
| **🔄 Schema Sync** | Automatic DB synchronization via `func_postgres_schema_init` on every startup. |
| **🧪 API Sandbox** | Interactive tester for real-time endpoint validation at `static/api/index.html`. |
| **📦 Global State** | Centralized access to Postgres, Redis, and S3 clients via `request.app.state`. |
| **👤 User Context** | Injected user identity and role data accessible via `request.state.user`. |
| **🛡️ Auth Guard** | Simple manual security enforcement: `if not request.state.user: raise Exception`. |
| **🔑 RBAC Control** | Built-in role-based access control (Supports: `realtime`, `token`, `inmemory`, `redis`). |
| **✅ Account Status** | Automated active-status enforcement (Supports: `realtime`, `token`, `inmemory`, `redis`). |
| **⚡ Smart Caching** | High-performance response caching (Supports: `inmemory`, `redis`). |
| **🚦 Rate Limiting** | Integrated traffic control and throttling (Supports: `inmemory`, `redis`). |

