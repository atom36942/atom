### about atom
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated and full flexible to extend
- Tech Stack:Python,FastAPI,Postgres,Redis,S3,Celery,RabbitMQ,Kafka,Sentry

### guides

<details>
<summary>setup (direct)</summary>

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
<summary>setup (docker)</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
</details>


<details>
<summary>run test</summary>

```bash
./venv/bin/python3.11 test.py
```
- Refer [curl.txt](file:///Users/atom/atom/curl.txt) for API list
- Refer [api.html](file:///Users/atom/atom/static/api.html) for API documentation
</details>

<details>
<summary>run consumer</summary>

```bash
venv/bin/python consumer.py celery
venv/bin/python consumer.py rabbitmq
venv/bin/python consumer.py redis
venv/bin/python consumer.py kafka
```
</details>

<details>
<summary>add router</summary>

1. `router.py`: Add route with correct prefix (`root`, `auth`, `my`, `public`, `private`, `admin`).
2. `function.py`: Add core logic as a pure function (local imports only).
3. `config.py`: Add any required `config_` variables.
4. `main.py`: Initialize relevant `client_` in lifespan.
5. `curl.txt` + `api.html`: Add test entry for sync.
</details>

<details>
<summary>enable caching</summary>

1. `config.py`: Add `cache_sec` to the endpoint configuration:
```python
config_api = {
    "/public/object-read": {
        "cache_sec": ("redis", 3600), # or "inmemory"
    }
}
```
2. The middleware in `main.py` handles the logic.
</details>

<details>
<summary>enable rate limit</summary>

1. `config.py`: Add `ratelimiter_times_sec` to the endpoint configuration:
```python
config_api = {
    "/auth/login": {
        "ratelimiter_times_sec": ("redis", 5, 60), # 5 requests per 60s
    }
}
```
2. The middleware in `main.py` handles the logic.
</details>

<details>
<summary>add task</summary>

1. Call `func_obj_create_logic` or `func_obj_update_logic` with `queue="celery"` (or `kafka`, `rabbitmq`, `redis`).
2. The logic is automatically routed to producers.
3. Workers in `consumer.py` handle the execution.
</details>

<details>
<summary>run sql</summary>

Use `func_postgres_runner` from `function.py`:
```python
await request.state.func_postgres_runner(
    request.state.client_postgres, 
    "read", 
    "SELECT * FROM users;"
)
```
</details>

<details>
<summary>develop</summary>

- Refer [AGENTS.md](file:///Users/atom/atom/AGENTS.md) for coding rules
- Refer [dev.md](file:///Users/atom/atom/static/dev.md) for personal notes & snippets
</details>

