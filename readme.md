<details>
<summary>About</summary>
<div style="padding-top: 10px;">

| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend framework to speed up large-scale application development. |
| **Architecture** | Modular architecture combining functional and procedural styles. |
| **Reliability** | Pure functions used to minimize side effects and improve testability. |
| **Production** | Ready to build APIs, background jobs, and integrations quickly. |
| **Efficiency** | Minimal boilerplate so you don’t have to reinvent the wheel each time. |
| **Flexibility** | Non-opinionated and fully flexible to extend. |
| **Tech Stack** | Python, FastAPI, Postgres, Redis, S3, Celery, RabbitMQ, Kafka, Sentry. |

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
<summary>Setup: Env Variable</summary>
<div style="padding-top: 10px;">

```bash
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
```

</div>
</details>

<details>
<summary>PostgreSQL: Database Initialization</summary>
<div style="padding-top: 10px;">

The schema and initial data are managed through an automated startup sequence and dedicated administrative endpoints.

| Feature | Logic Source | Behavior |
| :--- | :--- | :--- |
| **Lifecycle Init** | `Lifespan` (main.py) | Triggers `func_postgres_init` on startup if `config_is_postgres_init_startup=1`. |
| **System Sync** | `/admin/sync` | Orchestrates a full system refresh: DB init, schema caching, and temporary data cleaning. |
| **Data Seeding** | `func_postgres_init` | Automatically creates the root admin user (`atom`) and required extensions (e.g., `uuid-ossp`, `pg_trgm`). |

</div>
</details>

<details>
<summary>Administrative Control: System Management</summary>
<div style="padding-top: 10px;">

A suite of protected endpoints under the `/admin/` prefix provides direct control over the database, cache, and cloud infrastructure.

| Command / Endpoint | Responsibility | Behavior |
| :--- | :--- | :--- |
| **`/admin/postgres-runner`** | Raw Execution | Executes arbitrary SQL queries (Read/Write mode) directly on the Postgres pool. |
| **`/admin/postgres-export`** | Data Portability | Streams any SQL query result as a downloadable CSV file. |
| **`/admin/postgres-import`** | Bulk Ingestion | Processes CSV uploads for high-speed `create`, `update`, or `delete` operations. |
| **`/admin/sync`** | System Refresh | Re-initializes schema, updates local caches, and flushes persistent buffers. |
| **`/admin/object-read/update`**| Master CRUD | Provides unrestricted access to all tables, bypassing standard `creator_id` filters. |
| **`/admin/s3-bucket-ops`** | Cloud Infra | Direct control over bucket creation, permission toggles (public/private), and deletion. |

> [!IMPORTANT]
> Access to the `/admin/` prefix is strictly restricted to users with `role=1`. This is enforced by the centralized middleware pipeline and cannot be bypassed.

</div>
</details>


<details>
<summary>Environment Variables</summary>
<div style="padding-top: 10px;">

Environment variables can be defined in a `.env` file at the root of the project or exported directly in your shell. The framework automatically detects and applies these configurations on startup.

| Feature | Logic Source | Behavior |
| :--- | :--- | :--- |
| **Dynamic Overrides** | `config.py` | Any variable starting with `config_` can be overridden via `.env` or shell. |
| **Logic Provider** | `func_config_override_from_env` | Automated detection and application of environment configurations on startup. |
| **Type Conversion** | `function.py` | Automatic management of booleans (0/1), integers, and JSON objects. |


| Category | Environment Variable | Type | Sample Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | `config_postgres_url` | `str` | `postgresql://atom@127.0.0.1/postgres` | Connection URL for the primary database. |
| | `config_postgres_min_connection` | `int` | `5` | Minimum pool size (Default: 5). |
| | `config_postgres_max_connection` | `int` | `20` | Maximum pool size (Default: 20). |
| **Redis / Cache**| `config_redis_url` | `str` | `redis://localhost:6379` | Primary Redis connection string. |
| | `config_redis_url_ratelimiter`| `str` | `redis://localhost:6379` | Redis instance for rate limiting. |
| | `config_redis_cache_ttl_sec` | `int` | `3600` | TTL for cached API responses in seconds. |
| **Queues** | `config_rabbitmq_url` | `str` | `amqp://guest:guest@localhost:5672` | RabbitMQ connection URL. |
| | `config_kafka_url` | `str` | `localhost:9092` | Kafka broker URL. |
| | `config_celery_broker_url`| `str` | `-` | Celery broker URL (Defaults to Redis URL). |
| | `config_celery_backend_url`| `str` | `-` | Celery result backend URL. |
| **Security** | `config_token_secret_key` | `str` | `super-secret-key` | JWT signing secret. |
| | `config_token_expiry_sec` | `int` | `86400` | JWT token validity duration in seconds. |
| | `config_cors_origin` | `list` | `["*"]` | Allowed CORS origins (JSON array: `["*"]`). |
| **AI Providers** | `config_openai_key` | `str` | `sk-proj-...` | OpenAI API key for GPT integrations. |
| | `config_gemini_key` | `str` | `AIzaSy...` | Google Gemini API key. |
| **Cloud** | `config_aws_access_key_id` | `str` | `AKIA...` | AWS access key for S3, SNS, SES. |
| | `config_aws_secret_access_key`| `str` | `secret` | AWS secret key. |
| | `config_s3_region_name` | `str` | `us-east-1` | S3 bucket region. |
| | `config_sftp_host` | `str` | `localhost` | SFTP server hostname. |
| | `config_sftp_password` | `str` | `password` | SFTP password or key path. |
| **Integrations**| `config_sentry_dsn` | `str` | `https://...@sentry.io/...` | Sentry DSN for error tracking. |
| | `config_posthog_project_key`| `str` | `phc_...` | Posthog project key for analytics. |
| | `config_gsheet_service_account_json_path` | `str` | `./creds.json` | Path to Google Service Account JSON. |
| **Switches** | `config_is_signup` | `int` | `1` | Toggle user signup (1: Enabled, 0: Disabled).|
| | `config_is_log_api` | `int` | `1` | Toggle API logging (1: Enabled, 0: Disabled). |
| | `config_is_traceback` | `int` | `0` | Toggle Python traceback in responses (1/0). |
| | `config_is_prometheus` | `int` | `1` | Toggle `/metrics` prometheus endpoint (1/0). |
| | `config_is_reset_tmp` | `int` | `1` | Wipe `./tmp` folder on boot (1/0). |

</div>
</details>

<details>
<summary>Repository Map</summary>
<div style="padding-top: 10px;">

A high-level overview of the project architecture and file responsibilities.

| Path | Service | Responsibility |
| :--- | :--- | :--- |
| `main.py` | **Entry** | Lifespan, Middleware, App Initialization. |
| `router.py` | **API** | Definition of all endpoints and role assignments. |
| `function.py` | **Core** | Primary functional logic and database drivers. |
| `config.py` | **Settings** | Global configuration and schema definitions. |
| `consumer.py` | **Workers** | Background task processing (Celery, Kafka, etc.). |
| `static/` | **Assets** | Frontend files and documentation pages. |
| `script/` | **Shell** | Administrative scripts and maintenance utilities. |
| `requirements.txt`| **Deps** | Python package dependencies and environment requirements. |
| `Dockerfile` | **Infra** | Containerization logic for reproducible deployments. |
| `readme.md` | **Docs** | Primary project documentation and developer reference. |
| `AGENTS.md`| **Rules** | Agentic AI behavior standards and development protocols. |
| `.gitignore` | **Version** | Git tracking rules and repository exclusion settings. |

</div>
</details>

<details>
<summary>Service Integrations</summary>
<div style="padding-top: 10px;">

The framework provides pre-configured async clients for a wide range of production services.

| Category | Service Integration | Client / Function Source |
| :--- | :--- | :--- |
| **Databases** | PostgreSQL, Redis | `client_postgres_pool`, `client_redis` |
| **AI / ML** | OpenAI, Google Gemini | `client_openai`, `client_gemini` |
| **Cloud / S3** | Amazon S3, SNS, SES | `client_s3`, `client_sns`, `client_ses` |
| **Messaging** | Celery, Kafka, RabbitMQ, Redis | `client_*_producer` |
| **Analytics** | Posthog, Sentry | `client_posthog`, `func_app_add_sentry` |
| **Utilities** | SFTP, Google Sheets, HTTP | `client_sftp`, `client_gsheet`, `client_http` |

</div>
</details>

<details>
<summary>Middleware Pipeline</summary>
<div style="padding-top: 10px;">

Every incoming request passes through a strictly ordered validation and processing sequence.

| Order | Pipeline Stage | Behavior |
| :--- | :--- | :--- |
| **1** | **Authentication** | Decodes JWT and verifies identity via `func_authenticate`. |
| **2** | **Admin Check** | Ensures user has role `1` for all `/admin/` paths. |
| **3** | **Active Check** | Verifies `is_active=1` status from Redis/Postgres cache. |
| **4** | **Rate Limiting** | Enforces sliding window constraints per IP or User ID. |
| **5** | **Response Cache** | Returns pre-rendered Gzip/B64 responses if valid TTL exists. |
| **6** | **API Execution** | Processes the route-specific functional logic. |
| **7** | **API Logging** | Background log creation to `log_api` for all non-GET requests. |

</div>
</details>

<details>
<summary>Security: API Roles</summary>
<div style="padding-top: 10px;">

Path-based security is enforced automatically by the unified middleware pipeline.

| Prefix Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Identity flows (login, signup, OTP). |
| `/public/` | Public | General data access for non-registered users. |
| `/` | Public | Root indices and documentation. |
| `/my/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/private/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/admin/` | **Role-Based** | Requires token **AND** matching role in `config_api`. |

</div>
</details>

<details>
<summary>Security: User State Injection</summary>
<div style="padding-top: 10px;">

Authorized user context and global clients are injected into every request.

| Variable | Key Source | Properties |
| :--- | :--- | :--- |
| **`request.state.user`** | JWT Decoder | `id`, `type`, `role`, `is_active` |
| **`request.app.state`** | Lifespan Hooks | All `client_`, `config_`, and `func_` singletons. |

</div>
</details>


<details>
<summary>Queues & Consumer Workers</summary>
<div style="padding-top: 10px;">

| Protocol | Backend | Driver / Client | Run Consumer Command |
| :--- | :--- | :--- | :--- |
| **Celery** | Redis | `func_celery_producer` | `venv/bin/python consumer.py celery` |
| **Kafka** | Event Stream | `func_kafka_producer` | `venv/bin/python consumer.py kafka` |
| **RabbitMQ** | AMQP | `func_rabbitmq_producer` | `venv/bin/python consumer.py rabbitmq` |
| **Redis** | Pub/Sub | `func_redis_producer` | `venv/bin/python consumer.py redis` |

</div>
</details>

<details>
<summary>Assets: Content Delivery</summary>
<div style="padding-top: 10px;">

| Feature | Details | Logic |
| :--- | :--- | :--- |
| **Static** | `./static` | Served via the `/static/` URL prefix. |
| **Dynamic** | `/page-{name}` | Recursive HTML search via `func_html_serve`. |

</div>
</details>

<details>
<summary>API Tester: Discovery</summary>
<div style="padding-top: 10px;">

The `api.html` dashboard is **fully dynamic** and automated. New routes added to `router.py` appear automatically with their respective parameters rendered based on the Pydantic schema.

| Tab | Description |
| :--- | :--- |
| **Master** | Central discovery hub. Features real-time search, tag-based path filtering, and an interactive list of all discovered endpoints. |
| **Test** | Bulk testing suite. Allows selective or full-suite execution with live status tracking, latency metrics, and response inspection. |
| **Analytics** | Visual insights. Provides bar charts for API roles, HTTP methods, security distribution, and detailed test performance statistics. |
| **Storage** | Session state manager. Directly view and manage local storage entries, including active JWT tokens and persistent UI selections. |
| **Overrides** | Configuration preview. Displays the active `PATH_OVERRIDES` used to inject premium default values for complex testing scenarios. |

</div>
</details>



<details>
<summary>Package Management</summary>
<div style="padding-top: 10px;">

The Atom framework primarily utilizes `pip` with `venv`, but is fully compatible with modern dependency managers.

<details>
<summary>pip</summary>
<div style="padding-top: 10px;">

```bash
./venv/bin/pip install fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip install -r requirements.txt
./venv/bin/pip freeze > requirements.txt
```

</div>
</details>

<details>
<summary>poetry</summary>
<div style="padding-top: 10px;">

```bash
poetry add fastapi
poetry remove fastapi
poetry update fastapi
poetry install
poetry lock
```

</div>
</details>

<details>
<summary>conda</summary>
<div style="padding-top: 10px;">

```bash
conda install fastapi
conda remove fastapi
conda update fastapi
conda env create -f environment.yml
conda list --export > environment.yml
```

</div>
</details>

</div>
</details>
