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
<summary>setup</summary>

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
<summary>setup with docker</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
</details>

<details>
<summary>consumers</summary>

```bash
./venv/bin/python consumer.py celery
./venv/bin/python consumer.py rabbitmq
./venv/bin/python consumer.py redis
./venv/bin/python consumer.py kafka
```

<details>
<summary>api controls</summary>

### Configuring `config_api`
API behaviors like authentication, caching, and rate limiting are controlled per-route in the `config_api` dictionary.

| Setting Name | Modes Available | TTL / Parameter Source | Execution Logic |
| :--- | :--- | :--- | :--- |
| `user_is_active_check` | `redis`, `realtime`, `inmemory`, `token` | `config_redis_cache_ttl_sec` | Verifies `is_active=1` |
| `user_role_check` | `redis`, `realtime`, `inmemory`, `token` | `config_redis_cache_ttl_sec` | Matches IDs in list (e.g. `[1, 2]`) |
| `api_cache_sec` | `redis`, `inmemory` | Inbuilt (e.g. `["redis", 60]`) | Full Response Gzip/Base64 |
| `api_ratelimiting_times_sec` | `redis`, `inmemory` | Inbuilt (e.g. `["inmemory", 3, 10]`) | Sliding Window Counter |

### Mode Definitions
- **`redis`**: Distributed state via Redis keys.
- **`inmemory`**: Local state via `app.state` dictionaries.
- **`realtime`**: Live PostgreSQL queries for zero stale data.

</details>

<details>
<summary>authentication</summary>

### Route Protection
The framework enforces authentication automatically based on a unified path prefix system.

| Prefix Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Open for login, signup, and OTP flows. |
| `/public/` | Public | Unprotected data endpoints for general access. |
| `/` | Public | General root or marketing endpoints. |
| `/my/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/private/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/admin/` | **Role-Based** | Requires token **AND** matching role in `config_api`. |

### Manual Enforcement
For any public route where you want to selectively verify a user, check the `request.state.user` dictionary:

```python
# Force auth in a public route
if not request.state.user:
    raise Exception("unauthorized access")
```

### Context Injection
The `request.state.user` object is populated by the middleware using `func_authenticate`. It contains decoded JWT data (id, type, role, is_active) for use across any API function.

</details>

