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
```

###  FAQ
| What | Description |
| :--- | :--- |
| **Postgres Schema Init** | Automatic database synchronization (`func_postgres_schema_init`) executed on every startup. |
| **API Runner / Tester** | Interactive interface for API exploration and testing available at `static/api/index.html`. |
| **Global App State** | Access to shared clients (Postgres, Redis, S3, etc.) and caches via `request.app.state`. |
| **Authenticated User** | Injected user context (ID, Role, Username, etc.) accessible via `request.state.user`. |
| **Manual Auth Guard** | Enforce security manually using `if request.state.user is None: raise Exception("Unauthorized")`. |
| **Role Authorization** | Automated role-based access control via `user_role_check` in `config_api` (Supports: Realtime, Token, In-Memory, Redis). |
| **Status Authorization** | Automated account status enforcement via `user_is_active_check` in `config_api` (Supports: Realtime, Token, In-Memory, Redis). |
| **API Response Cache** | Highly configurable caching via `api_cache_sec` in `config_api` (Supports: In-Memory, Redis). |
| **API Rate Limiter** | Traffic control via `api_ratelimiting_times_sec` in `config_api` (Supports: In-Memory, Redis). |
| **Postgres Schema DSL** | Supported column configuration keys: `name`, `datatype`, `default`, `index`, `unique`, `is_mandatory`, `regex`, `in`, `check`, `old`. |
| **API Parameter DSL** | Parameter definition tuple: `name`, `datatype`, `is_mandatory`, `allowed_values`, `default`, `description`, `regex_info`. |
| **Username Validation** | Rules: 3-20 characters, alphanumeric start/end, allowed middle symbols (`_`, `@`, `-`). |
| **Password Validation** | Rules: 8-32 characters, no whitespace, supports high-entropy symbols. |
| **Email Validation** | Standard RFC-compliant email regex validation. |
| **Mobile Validation** | International format support (8-15 digits, optional `+` prefix). |
| **Root Account Sync** | Mandatory ID 1 lifecycle: `username='atom'`, `role=1`, `is_active=1`. Password is set only during initial database creation. |
| **Application Guard** | Strict startup consistency checks: Duplicate Config Keys, Route Discovery Mapping, Admin API Role Enforcement, Invalid Middleware Modes, Strict CORS Wildcard Rules, Boolean Switch Validation, Unique API ID Enforcement, Table & Column Integrity, Redundant Non-Unique Index Detection, Root User Presence. |

