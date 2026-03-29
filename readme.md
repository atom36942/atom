### about
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated and full flexible to extend
- Tech Stack: Python, FastAPI, Postgres, Redis, S3, Celery, RabbitMQ, Kafka, Sentry

<details>
<summary>setup direct</summary>

```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -V
./venv/bin/uvicorn main:app --reload
```
</details>

<details>
<summary>setup docker</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
</details>

<details>
<summary>consumer run</summary>

```bash
./venv/bin/python consumer.py celery
./venv/bin/python consumer.py rabbitmq
./venv/bin/python consumer.py redis
./venv/bin/python consumer.py kafka
```
</details>

<details>
<summary>api cache set</summary>

Configured per route in `config_api` inside `config.py`.

- **Field**: `cache_sec`
- **Format**: `["mode", seconds]`
- **Modes**:
  - `inmemory`: fast, non-persistent, local node only
  - `redis`: shared across instances, requires `config_redis_url`
  
Example:
```python
"/my/profile": {"cache_sec": ["inmemory", 60]}
"/public/posts": {"cache_sec": ["redis", 3600]}
```
</details>

<details>
<summary>ratelimiter set</summary>

Configured per route in `config_api` inside `config.py`.

- **Field**: `ratelimiter_times_sec`
- **Format**: `["mode", limit, window_seconds]`
- **Modes**:
  - `inmemory`: local window per instance
  - `redis`: global window across instances, requires `config_redis_url_ratelimiter`

Example:
```python
"/test": {"ratelimiter_times_sec": ["inmemory", 10, 60]} # 10 requests per 60s
"/auth/login": {"ratelimiter_times_sec": ["redis", 5, 1]}  # 5 requests per 1s
```
</details>

<details>
<summary>core config toggle</summary>

High-level switches and modes in `config.py`:

- `config_is_signup`: (1/0) Enable/disable public signup
- `config_is_log_api`: (1/0) Save API logs to `log_api` table
- `config_is_traceback`: (1/0) Return full traceback on 500 error
- `config_mode_check_active`: (`realtime`, `cache`, `token`) Mode for user status validation
- `config_mode_check_admin`: (`realtime`, `cache`, `token`) Mode for admin role validation
- `config_is_prometheus`: (1/0) Enable metrics endpoint at `/metrics`
- `config_is_debug_fastapi`: (1/0) Enable FastAPI internal debug mode
</details>

<details>
<summary>active check set</summary>

Configures how user activity status is verified on each request.

- **Field**: `config_mode_check_active`
- **Modes**:
  - `token`: Read `is_active` directly from JWT payload (fastest)
  - `cache`: Check against memory-cached status (balanced)
  - `realtime`: Query PostgreSQL on every request (most accurate)

> [!NOTE]
> `cache` mode uses `cache_users_is_active` populated at application startup.
</details>

<details>
<summary>admin check set</summary>

Configures how administrative roles are verified for `/admin` routes.

- **Field**: `config_mode_check_admin`
- **Modes**:
  - `token`: Read `role` directly from JWT payload (fastest)
  - `cache`: Check against memory-cached roles (balanced)
  - `realtime`: Query PostgreSQL on every request (most accurate)

> [!NOTE]
> `cache` mode uses `cache_users_role` populated at application startup.
</details>


