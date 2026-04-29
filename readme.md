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
| **Postgres Init** | Automatic `func_postgres_schema_init` run on startup. |
| **API Master** | Interactive API tester at `static/api/index.html`. |
| **Access App State** | Global clients (DB, Redis, etc.) via `request.app.state`. |
| **User Context** | Current user state (id, role, etc.) via `request.state.user`. |
| **Manual Auth Check** | Check via `if request.state.user is None: raise Exception("Unauthorized")`. |
| **Admin Check** | Role checks via `user_role_check` in `config_api` (Modes: realtime, token, inmemory, redis). |
| **User Active Check** | Status checks via `user_is_active_check` in `config_api` (Modes: realtime, token, inmemory, redis). |
| **API Caching** | Cache logic via `api_cache_sec` in `config_api` (Modes: inmemory, redis). |
| **API Ratelimiter** | Rate limits via `api_ratelimiting_times_sec` in `config_api` (Modes: inmemory, redis). |
| **Postgres Column Control** | Column control keys: `name`, `datatype`, `default`, `index`, `unique`, `is_mandatory`, `regex`, `in`, `check`, `old`. |
| **API Param Control** | Config tuple for `func_request_param_read`: `name`, `datatype`, `is_mandatory`, `allowed_values`, `default`, `description`, `regex_info` (pattern, error). |
| **Username Regex** | Rules: 3-20 chars, start/end with `a-z0-9`, symbols `_`, `@`, `-` middle only. Examples: `7eleven` ✅, `admin_atom` ✅, `user_` ❌, `_user` ❌, `user.name` ❌. |
| **Password Regex** | Rules: 8-32 chars, no spaces. Examples: `Password@123` ✅, `@Admin123` ✅, `User#2026!` ✅, `pass 123` ❌, `short` ❌. |
| **Email Regex** | Rules: Basic email format (`user@domain.com`). Examples: `test@atom.com` ✅, `user+tag@work.co` ✅, `invalid-email` ❌. |
| **Mobile Regex** | Rules: 8-15 digits, may start with `+`. Examples: `+919876543210` ✅, `9876543210` ✅, `1234567` ❌, `+0123456789` ❌. |
| **Root User Sync** | ID 1 metadata resets on restart: `type=1`, `username='atom'`, `role=1`, `is_active=1`. Password is only set from `config_postgres_root_user_password` during first creation. |

