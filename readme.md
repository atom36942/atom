### atom
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated and full flexible to extend
- Tech Stack:Python,FastAPI,Postgres,Redis,S3,Celery,RabbitMQ,Kafka,Sentry

### guides

<details>
<summary>how to setup (direct)</summary>

```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv/ && /opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
python -V
```
</details>

<details>
<summary>how to setup (docker)</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
</details>

<details>
<summary>how to run server</summary>

```bash
./venv/bin/uvicorn main:app --reload
```
</details>

<details>
<summary>how to run test</summary>

```bash
./venv/bin/python3.11 test.py
```
- Refer [curl.txt](file:///Users/atom/atom/curl.txt) for API list
- Refer [api.html](file:///Users/atom/atom/static/api.html) for API documentation
</details>

<details>
<summary>how to run consumer (celery/kafka/rabbitmq/redis)</summary>

```bash
venv/bin/python consumer.py celery
venv/bin/python consumer.py rabbitmq
venv/bin/python consumer.py redis
venv/bin/python consumer.py kafka
```
</details>

<details>
<summary>how to add a new router</summary>

1. `router.py`: Add route with correct prefix (`root`, `auth`, `my`, `public`, `private`, `admin`).
2. `function.py`: Add core logic as a pure function (local imports only).
3. `config.py`: Add any required `config_` variables.
4. `main.py`: Initialize relevant `client_` in lifespan.
5. `curl.txt` + `api.html`: Add test entry for sync.
</details>

<details>
<summary>how to enable api caching</summary>

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
<summary>how to enable rate limiting</summary>

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
<summary>how to add a background task</summary>

1. Call `func_obj_create_logic` or `func_obj_update_logic` with `queue="celery"` (or `kafka`, `rabbitmq`, `redis`).
2. The logic is automatically routed to producers.
3. Workers in `consumer.py` handle the execution.
</details>

<details>
<summary>how to run raw sql</summary>

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
<summary>how to develop with agents</summary>

- Refer [AGENTS.md](file:///Users/atom/atom/AGENTS.md) for coding rules
- Refer [dev.md](file:///Users/atom/atom/static/dev.md) for personal notes & snippets
</details>

### module guide
- PostgreSQL: one-click setup, CSV upload, query runner
- Auth & RBAC: auth APIs, user/admin APIs
- Performance: Redis cache, rate limiting
- Async & Queues: Celery, Kafka, RabbitMQ, Redis pub/sub
- Integrations: Sentry, MongoDB, PostHog
- Messaging: OTP (Fast2SMS, Resend), AWS S3/SNS/SES
- Data Ops: bulk insert/update, Google Sheets, SFTP
- Platform: HTML serving, multi-tenant support, extensible architecture
