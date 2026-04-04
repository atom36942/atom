<details>
<summary>About</summary>
<div style="padding-top: 10px;">

| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend for rapid large-scale development. |
| **Architecture** | Modular setup combining functional and procedural styles. |
| **Reliability** | Pure functions to minimize side effects and improve testing. |
| **Production** | Rapidly build APIs, background jobs, and integrations. |
| **Efficiency** | Minimal boilerplate to avoid reinventing the wheel. |
| **Flexibility** | Non-opinionated and fully extensible framework. |
| **Tech Stack** | FastAPI, Postgres, Redis, RabbitMQ, Kafka, Celery, S3. |

</div>
</details>


<details>
<summary>Setup: GitHub SSH</summary>
<div style="padding-top: 10px;">

```bash
ssh-keygen -t ed25519 -C "email"
cat ~/.ssh/id_ed25519.pub
ssh -T git@github.com
git clone git@github.com:atom36942/atom.git
cd atom
git remote set-url origin git@github.com:atom36942/atom.git
git pull origin main
git add .
git commit -m "sync"
git push origin main
```

</div>
</details>

<details>
<summary>Setup: Brew</summary>
<div style="padding-top: 10px;">

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install python@3.11
brew install postgis
brew install postgresql && brew install redis && brew install rabbitmq && echo 'export PATH="/opt/homebrew/sbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
brew services start postgresql && brew services start redis && brew services start rabbitmq
brew services restart postgresql && brew services restart redis && brew services start rabbitmq
brew services stop postgresql && brew services stop redis && brew services stop rabbitmq
brew update && brew upgrade postgresql && brew upgrade redis && brew upgrade rabbitmq && brew services restart --all
brew services stop --all && brew uninstall --force postgresql && brew uninstall --force redis && brew uninstall --force rabbitmq && rm -rf /opt/homebrew/var/postgres /opt/homebrew/var/db/redis /opt/homebrew/var/lib/rabbitmq && brew cleanup
psql --version && redis-cli --version && rabbitmqctl version
brew services list
```

</div>
</details>

<details>
<summary>Setup: Local Deployment</summary>
<div style="padding-top: 10px;">

```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -V
./venv/bin/python main.py
./venv/bin/uvicorn main:app --reload
```

</div>
</details>

<details>
<summary>Setup: Docker Deployment</summary>
<div style="padding-top: 10px;">

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```

</div>
</details>

<details>
<summary>Setup: Environment Variables</summary>
<div style="padding-top: 10px;">

Environment variables can be defined in a `.env` file at the root of the project or exported directly in your shell. The framework automatically detects and applies these configurations on startup.

| Category | Environment Variable | Type | Sample Value |
| :--- | :--- | :--- | :--- |
| **Postgres** | `config_postgres_url` | `str` | `postgresql://user:pass@host/db` |
| | `config_postgres_min_connection` | `int` | `5` |
| | `config_postgres_max_connection` | `int` | `20` |
| **Redis** | `config_redis_url` | `str` | `redis://localhost:6379` |
| | `config_redis_cache_ttl_sec` | `int` | `3600` |
| **Queues** | `config_rabbitmq_url` | `str` | `amqp://guest:guest@localhost:5672` |
| | `config_kafka_url` | `str` | `localhost:9092` |
| **Security** | `config_token_secret_key` | `str` | `super-secret-key` |
| | `config_token_expiry_sec` | `int` | `86400` |
| **AI** | `config_openai_key` | `str` | `sk-proj-...` |
| | `config_gemini_key` | `str` | `AIzaSy...` |
| **Cloud** | `config_aws_access_key_id` | `str` | `AKIA...` |
| | `config_s3_region_name` | `str` | `us-east-1` |
| **Integrations** | `config_sentry_dsn` | `str` | `https://...@sentry.io/...` |
| | `config_posthog_project_key` | `str` | `phc_...` |
| **Switches** | `config_is_signup` | `int` | `1` |
| | `config_is_log_api` | `int` | `1` |
| | `config_is_prometheus` | `int` | `1` |


</div>
</details>


<details>
<summary>PostgreSQL: Database Initialization</summary>
<div style="padding-top: 10px;">

The schema and initial data are managed through an automated startup sequence and dedicated administrative endpoints.

| Feature | Logic Source | Behavior |
| :--- | :--- | :--- |
| **Lifecycle Init** | `Lifespan` | Runs `func_postgres_init` on startup. |
| **System Sync** | `/admin/sync` | Full system refresh: DB, schema, and cleaning. |


</div>
</details>

<details>
<summary>Administrative Control: System Management</summary>
<div style="padding-top: 10px;">

A suite of protected endpoints under the `/admin/` prefix provides direct control over the database, cache, and cloud infrastructure.

| Endpoint | Responsibility | Behavior |
| :--- | :--- | :--- |
| **`/admin/postgres-runner`** | Raw Execution | Executes arbitrary SQL directly on the pool. |
| **`/admin/postgres-export`** | Portability | Streams SQL results to downloadable CSV. |
| **`/admin/postgres-import`** | Bulk Ingestion | High-speed CSV ingestion for CRUD ops. |
| **`/admin/sync`** | System Refresh | Syncs schema, caches, and persistent buffers. |
| **`/admin/object-read/update`**| Master CRUD | Unrestricted table access (no creator filters). |
| **`/admin/s3-bucket-ops`** | Cloud Infra | Direct bucket creation and permission control. |


> [!IMPORTANT]
> Access to the `/admin/` prefix is strictly restricted to users with `role=1`. This is enforced by the centralized middleware pipeline and cannot be bypassed.

</div>
</details>

<details>
<summary>Repository Map</summary>
<div style="padding-top: 10px;">

A high-level overview of the project architecture and file responsibilities.

| Path | Service | Responsibility |
| :--- | :--- | :--- |
| `main.py` | **Entry** | App initialization and middleware handling. |
| `router.py` | **API** | Endpoint mapping and role assignments. |
| `function.py` | **Core** | Functional logic and database drivers. |
| `config.py` | **Settings** | Global settings and schema definitions. |
| `consumer.py` | **Workers** | Background task processing (Celery, Kafka). |
| `static/` | **Assets** | Frontend files and documentation pages. |
| `readme.md` | **Docs** | Project documentation and developer reference. |
| `AGENTS.md`| **Rules** | AI behavior standards and dev protocols. |


</div>
</details>

<details>
<summary>Service Integrations</summary>
<div style="padding-top: 10px;">

The framework provides pre-configured async clients for a wide range of production services.

| Category | Service | Client / Source |
| :--- | :--- | :--- |
| **Databases** | Postgres, Redis | `client_postgres_pool`, `client_redis` |
| **AI** | OpenAI, Gemini | `client_openai`, `client_gemini` |
| **Cloud** | S3, SNS, SES | `client_s3`, `client_sns`, `client_ses` |
| **Queues** | Celery, Kafka | `client_*_producer` |
| **Analytics** | Posthog, Sentry | `client_posthog`, `func_app_add_sentry` |
| **Utils** | SFTP, GSheets | `client_sftp`, `client_gsheet` |


</div>
</details>

<details>
<summary>Middleware Pipeline</summary>
<div style="padding-top: 10px;">

Every incoming request passes through a strictly ordered validation and processing sequence.

| Order | Pipeline Stage | Behavior |
| :--- | :--- | :--- |
| **1** | **Authentication** | JWT decoding and identity verification. |
| **2** | **Admin Check** | Enforces admin role for `/admin/` paths. |
| **3** | **Active Check** | Checks `is_active=1` status from cache. |
| **4** | **Rate Limiting** | Enforces IP/User sliding window constraints. |
| **5** | **Response Cache** | Returns Gzip/B64 cache if TTL is valid. |
| **6** | **API Execution** | Processes main functional logic. |
| **7** | **API Logging** | Logs non-GET requests in background. |


</div>
</details>

<details>
<summary>Security: API Roles</summary>
<div style="padding-top: 10px;">

Path-based security is enforced automatically by the unified middleware pipeline.

| Prefix Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Auth flows (login, signup, OTP). |
| `/public/` | Public | Data access for non-registered users. |
| `/my/` | **Protected** | Requires valid Bearer token. |
| `/private/` | **Protected** | Requires valid Bearer token. |
| `/admin/` | **Role-Based** | Requires token and admin role. |


</div>
</details>

<details>
<summary>Security: User State Injection</summary>
<div style="padding-top: 10px;">

Authorized user context and global clients are injected into every request.

| Variable | Key Source | Properties |
| :--- | :--- | :--- |
| **`request.state.user`** | JWT Decoder | `id`, `type`, `role`, `is_active` |
| **`request.app.state`** | Lifespan Hooks | All `client_` and `config_` singletons. |


</div>
</details>


<details>
<summary>Queues & Consumer Workers</summary>
<div style="padding-top: 10px;">

| Protocol | Backend | Driver | Run Consumer |
| :--- | :--- | :--- | :--- |
| **Celery** | Redis | `func_celery_producer` | `python consumer.py celery` |
| **Kafka** | Event Stream | `func_kafka_producer` | `python consumer.py kafka` |
| **RabbitMQ** | AMQP | `func_rabbitmq_producer` | `python consumer.py rabbitmq` |
| **Redis** | Pub/Sub | `func_redis_producer` | `python consumer.py redis` |


</div>
</details>

<details>
<summary>Assets: Content Delivery</summary>
<div style="padding-top: 10px;">

| Feature | Details | Logic |
| :--- | :--- | :--- |
| **Static** | `./static` | Served via `/static/` prefix. |
| **Dynamic** | `/page-{name}` | HTML search via `func_html_serve`. |


</div>
</details>

<details>
<summary>API Tester: Discovery</summary>
<div style="padding-top: 10px;">

The `api.html` dashboard is **fully dynamic** and automated. New routes added to `router.py` appear automatically with their respective parameters rendered based on the Pydantic schema.

| Tab | Description |
| :--- | :--- |
| **Master** | Central discovery hub with real-time search and filters. |
| **Test** | Bulk testing suite with latency tracking and inspection. |
| **Analytics** | Visual insights, role charts, and performance stats. |
| **Storage** | session manager for JWT and persistent UI state. |
| **Overrides** | Preview of `PATH_OVERRIDES` for test scenarios. |


</div>
</details>
