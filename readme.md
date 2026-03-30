<details>
<summary>about</summary>

- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated and full flexible to extend
- Tech Stack: Python, FastAPI, Postgres, Redis, S3, Celery, RabbitMQ, Kafka, Sentry
</details>

<details>
<summary>how to setup directly</summary>

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
<summary>how to setup with docker</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
</details>

<details>
<summary>how to run consumer workers</summary>

```bash
./venv/bin/python consumer.py celery
./venv/bin/python consumer.py rabbitmq
./venv/bin/python consumer.py redis
./venv/bin/python consumer.py kafka
```
</details>

<details>
<summary>how to enable api caching</summary>

Configured per route in `config_api` inside `config.py`.

- **Field**: `api_cache_sec`
- **Format**: `["mode", seconds]`
- **Modes**:
  - `inmemory`: fast, non-persistent, local node only
  - `redis`: shared across instances, requires `config_redis_url`
  
Example:
```python
"/my/profile": {"api_cache_sec": ["inmemory", 60]}
"/public/posts": {"api_cache_sec": ["redis", 3600]}
```
</details>

<details>
<summary>how to configure rate limiting</summary>

Configured per route in `config_api` inside `config.py`.

- **Field**: `api_ratelimiting_times_sec`
- **Format**: `["mode", limit, window_seconds]`
- **Modes**:
  - `inmemory`: local window per instance
  - `redis`: global window across instances, requires `config_redis_url_ratelimiter`

Example:
```python
"/test": {"api_ratelimiting_times_sec": ["inmemory", 10, 60]} # 10 requests per 60s
"/auth/login": {"api_ratelimiting_times_sec": ["redis", 5, 1]}  # 5 requests per 1s
```
</details>

<details>
<summary>how to set user active check mode</summary>

Configures how user activity status is verified on each request to determine if they can access an API. This checks the `is_active` column in the `users` table.

- **Field**: `user_is_active_check` (configured per route in `config_api`)
- **Format**: `["mode", 1]` (where 1 enables the check)
- **Modes**:
  - `token`: Read `is_active` directly from JWT payload (fastest)
  - `cache`: Check against memory-cached status (balanced)
  - `redis`: Check Redis cache with PostgreSQL fallback (distributed)
  - `realtime`: Query PostgreSQL on every request (most accurate)

> [!NOTE]
> `cache` mode uses `cache_users_is_active` populated at application startup.
</details>

<details>
<summary>how to set admin role check mode</summary>

Configures how administrative roles are verified for `/admin` routes.

- **Field**: `user_role_check` (configured per route in `config_api`)
- **Format**: `["mode", [allowed_roles]]`
- **Modes**:
  - `token`: Read `role` directly from JWT payload (fastest)
  - `cache`: Check against memory-cached roles (balanced)
  - `redis`: Check Redis cache with PostgreSQL fallback (distributed)
  - `realtime`: Query PostgreSQL on every request (most accurate)

> [!NOTE]
> `cache` mode uses `cache_users_role` populated at application startup.
</details>

<details>
<summary>how to configure rbac roles</summary>

Access control is defined per route in `config_api` inside `config.py`.

- **Field**: `user_role_check`
- **Format**: `["mode", [role_id_1, role_id_2, ...]]`
- **Logic**: If the user's `role` (from token/DB) is not in this list, access is denied.

Example:
```python
"/admin/sync": {"user_role_check": ["realtime", [1]]} # Only Admin (Role 1), Realtime DB check
"/test": {"user_role_check": ["token", [1, 2, 3]]} # Admin, Manager, User, JWT-based role
```

> [!TIP]
> Use `user_role_check` instead of boolean flags for more granular control over multi-tenant or multi-tier access.
</details>


<details>
<summary>how to make an api authenticated</summary>

```python
@router.get("/my/secure")
async def func_api_secure(request: Request):
    # Ensure a user is authenticated
    if not request.state.user:
        raise Exception("authorization token missing")
    return {"status": 1, "message": "you are authorized"}
```

**Optional header read example**

```python
@router.get("/test")
async def func_api_test(request: Request):
    # Header is optional; will raise if missing when mandatory flag is 1
    obj_header = await func_request_param_read(
        "header",
        request,
        [("authorization", "str", 0, None, None)]
    )
    token = obj_header.get("authorization")
    # token will be raw "Bearer <jwt>" if supplied
    return {"status": 1, "auth_provided": bool(token)}
```

> [!NOTE]
> The middleware (`func_check_token`) runs before every request and populates `request.state.user` when a valid Bearer token is present. Public routes (`/test`, `/public/*`) will not raise an error if the token is absent.

```bash
# Example curl with token
curl -H "Authorization: Bearer <your_jwt>" http://127.0.0.1:8000/my/secure
```
</details>
