<details>
<summary>About</summary>
<div style="padding-top: 10px;">

<div style="overflow-x: auto;">
| Core&nbsp;Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend framework to speed up large-scale application development. |
| **Architecture** | Modular architecture combining functional and procedural styles. |
| **Reliability** | Pure functions used to minimize side effects and improve testability. |
| **Production** | Ready to build APIs, background jobs, and integrations quickly. |
| **Efficiency** | Minimal boilerplate so you don’t have to reinvent the wheel each time. |
| **Flexibility** | Non-opinionated and fully flexible to extend. |
| **Tech Stack** | Python, FastAPI, Postgres, Redis, S3, Celery, RabbitMQ, Kafka, Sentry. |
</div>

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
<summary>Environment Variables</summary>
<div style="padding-top: 10px;">

Environment variables can be defined in a `.env` file at the root of the project or exported directly in your shell. The framework automatically detects and applies these configurations on startup.

<div style="overflow-x: auto;">
| Category | Environment&nbsp;Variable | Type | Sample Value |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | `config_postgres_url` | `str` | `postgresql://atom@127.0.0.1/postgres` |
| | `config_postgres_min_connection` | `int` | `5` |
| | `config_postgres_max_connection` | `int` | `20` |
| **Redis&nbsp;/&nbsp;Cache** | `config_redis_url` | `str` | `redis://localhost:6379` |
| | `config_redis_url_ratelimiter` | `str` | `redis://localhost:6379` |
| | `config_redis_cache_ttl_sec` | `int` | `3600` |
| **Queues** | `config_rabbitmq_url` | `str` | `amqp://guest:guest@localhost:5672` |
| | `config_kafka_url` | `str` | `localhost:9092` |
| | `config_celery_broker_url` | `str` | `-` |
| | `config_celery_backend_url` | `str` | `-` |
| **Security** | `config_token_secret_key` | `str` | `super-secret-key` |
| | `config_token_expiry_sec` | `int` | `86400` |
| | `config_cors_origin` | `list` | `["*"]` |
| **AI&nbsp;Providers** | `config_openai_key` | `str` | `sk-proj-...` |
| | `config_gemini_key` | `str` | `AIzaSy...` |
| **Cloud** | `config_aws_access_key_id` | `str` | `AKIA...` |
| | `config_aws_secret_access_key` | `str` | `secret` |
| | `config_s3_region_name` | `str` | `us-east-1` |
| | `config_sftp_host` | `str` | `localhost` |
| | `config_sftp_password` | `str` | `password` |
| **Integrations** | `config_sentry_dsn` | `str` | `https://...@sentry.io/...` |
| | `config_posthog_project_key` | `str` | `phc_...` |
| | `config_gsheet_service_account_json_path` | `str` | `./creds.json` |
| **Switches** | `config_is_signup` | `int` | `1` |
| | `config_is_log_api` | `int` | `1` |
| | `config_is_traceback` | `int` | `0` |
| | `config_is_prometheus` | `int` | `1` |
| | `config_is_reset_tmp` | `int` | `1` |
</div>


</div>
</details>


<details>
<summary>PostgreSQL: Database Initialization</summary>
<div style="padding-top: 10px;">

The schema and initial data are managed through an automated startup sequence and dedicated administrative endpoints.

<div style="overflow-x: auto;">
| Feature | Logic&nbsp;Source | Behavior |
| :--- | :--- | :--- |
| **Lifecycle&nbsp;Init** | `Lifespan`&nbsp;(main.py) | Triggers `func_postgres_init` on startup<br>if `config_is_postgres_init_startup=1`. |
| **System&nbsp;Sync** | `/admin/sync` | Orchestrates a full system refresh:<br>DB init, schema caching, and cleaning. |
</div>


</div>
</details>

<details>
<summary>Administrative Control: System Management</summary>
<div style="padding-top: 10px;">

A suite of protected endpoints under the `/admin/` prefix provides direct control over the database, cache, and cloud infrastructure.

<div style="overflow-x: auto;">
| Command&nbsp;/&nbsp;Endpoint | Responsibility | Behavior |
| :--- | :--- | :--- |
| **`/admin/postgres-runner`** | Raw&nbsp;Execution | Executes arbitrary SQL queries (Read/Write mode)<br>directly on the Postgres pool. |
| **`/admin/postgres-export`** | Data&nbsp;Portability | Streams any SQL query result as a<br>downloadable CSV file. |
| **`/admin/postgres-import`** | Bulk&nbsp;Ingestion | Processes CSV uploads for high-speed<br>`create`, `update`, or `delete` operations. |
| **`/admin/sync`** | System&nbsp;Refresh | Re-initializes schema, updates local caches,<br>and flushes persistent buffers. |
| **`/admin/object-read/update`**| Master&nbsp;CRUD | Provides unrestricted access to all tables,<br>bypassing standard `creator_id` filters. |
| **`/admin/s3-bucket-ops`** | Cloud&nbsp;Infra | Direct control over bucket creation, permission<br>toggles (public/private), and deletion. |
</div>


> [!IMPORTANT]
> Access to the `/admin/` prefix is strictly restricted to users with `role=1`. This is enforced by the centralized middleware pipeline and cannot be bypassed.

</div>
</details>

<details>
<summary>Repository Map</summary>
<div style="padding-top: 10px;">

A high-level overview of the project architecture and file responsibilities.

<div style="overflow-x: auto;">
| Path | Service | Responsibility |
| :--- | :--- | :--- |
| `main.py` | **Entry** | Lifespan, Middleware, App&nbsp;Initialization. |
| `router.py` | **API** | Definition of all endpoints and role&nbsp;assignments. |
| `function.py` | **Core** | Primary functional logic and database&nbsp;drivers. |
| `config.py` | **Settings** | Global configuration and schema&nbsp;definitions. |
| `consumer.py` | **Workers** | Background task processing (Celery, Kafka,&nbsp;etc.). |
| `static/` | **Assets** | Frontend files and documentation&nbsp;pages. |
| `script/` | **Shell** | Administrative scripts and maintenance&nbsp;utilities. |
| `requirements.txt`| **Deps** | Python package dependencies and environment&nbsp;requirements. |
| `Dockerfile` | **Infra** | Containerization logic for reproducible&nbsp;deployments. |
| `readme.md` | **Docs** | Primary project documentation and developer&nbsp;reference. |
| `AGENTS.md`| **Rules** | Agentic AI behavior standards and development&nbsp;protocols. |
| `.gitignore` | **Version** | Git tracking rules and repository exclusion&nbsp;settings. |
</div>


</div>
</details>

<details>
<summary>Service Integrations</summary>
<div style="padding-top: 10px;">

The framework provides pre-configured async clients for a wide range of production services.

<div style="overflow-x: auto;">
| Category | Service&nbsp;Integration | Client&nbsp;/&nbsp;Function&nbsp;Source |
| :--- | :--- | :--- |
| **Databases** | PostgreSQL, Redis | `client_postgres_pool`, `client_redis` |
| **AI&nbsp;/&nbsp;ML** | OpenAI, Google&nbsp;Gemini | `client_openai`, `client_gemini` |
| **Cloud&nbsp;/&nbsp;S3** | Amazon S3, SNS, SES | `client_s3`, `client_sns`, `client_ses` |
| **Messaging** | Celery, Kafka, RabbitMQ | `client_*_producer` |
| **Analytics** | Posthog, Sentry | `client_posthog`, `func_app_add_sentry` |
| **Utilities** | SFTP, GSheets, HTTP | `client_sftp`, `client_gsheet`, `client_http` |
</div>


</div>
</details>

<details>
<summary>Middleware Pipeline</summary>
<div style="padding-top: 10px;">

Every incoming request passes through a strictly ordered validation and processing sequence.

<div style="overflow-x: auto;">
| Order | Pipeline&nbsp;Stage | Behavior |
| :--- | :--- | :--- |
| **1** | **Authentication** | Decodes JWT and verifies identity<br>via `func_authenticate`. |
| **2** | **Admin&nbsp;Check** | Ensures user has role `1`<br>for all `/admin/` paths. |
| **3** | **Active&nbsp;Check** | Verifies `is_active=1` status<br>from Redis/Postgres cache. |
| **4** | **Rate&nbsp;Limiting** | Enforces sliding window constraints<br>per IP or User ID. |
| **5** | **Response&nbsp;Cache** | Returns pre-rendered Gzip/B64 responses<br>if valid TTL exists. |
| **6** | **API&nbsp;Execution** | Processes the route-specific<br>functional logic. |
| **7** | **API&nbsp;Logging** | Background log creation for<br>all non-GET requests. |
</div>


</div>
</details>

<details>
<summary>Security: API Roles</summary>
<div style="padding-top: 10px;">

Path-based security is enforced automatically by the unified middleware pipeline.

<div style="overflow-x: auto;">
| Prefix&nbsp;Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Identity flows (login, signup, OTP). |
| `/public/` | Public | General data access for non-registered users. |
| `/` | Public | Root indices and documentation. |
| `/my/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/private/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/admin/` | **Role-Based** | Requires token **AND** matching<br>role in `config_api`. |
</div>


</div>
</details>

<details>
<summary>Security: User State Injection</summary>
<div style="padding-top: 10px;">

Authorized user context and global clients are injected into every request.

<div style="overflow-x: auto;">
| Variable | Key&nbsp;Source | Properties |
| :--- | :--- | :--- |
| **`request.state.user`** | JWT Decoder | `id`, `type`, `role`, `is_active` |
| **`request.app.state`** | Lifespan Hooks | All `client_`, `config_`, and `func_` singletons. |
</div>


</div>
</details>


<details>
<summary>Queues & Consumer Workers</summary>
<div style="padding-top: 10px;">

<div style="overflow-x: auto;">
| Protocol | Backend | Driver&nbsp;/&nbsp;Client | Run&nbsp;Consumer&nbsp;Command |
| :--- | :--- | :--- | :--- |
| **Celery** | Redis | `func_celery_producer` | `venv/bin/python consumer.py celery` |
| **Kafka** | Event&nbsp;Stream | `func_kafka_producer` | `venv/bin/python consumer.py kafka` |
| **RabbitMQ** | AMQP | `func_rabbitmq_producer` | `venv/bin/python consumer.py rabbitmq` |
| **Redis** | Pub/Sub | `func_redis_producer` | `venv/bin/python consumer.py redis` |
</div>


</div>
</details>

<details>
<summary>Assets: Content Delivery</summary>
<div style="padding-top: 10px;">

<div style="overflow-x: auto;">
| Feature | Details | Logic |
| :--- | :--- | :--- |
| **Static** | `./static` | Served via the `/static/` URL prefix. |
| **Dynamic** | `/page-{name}` | Recursive HTML search via `func_html_serve`. |
</div>


</div>
</details>

<details>
<summary>API Tester: Discovery</summary>
<div style="padding-top: 10px;">

The `api.html` dashboard is **fully dynamic** and automated. New routes added to `router.py` appear automatically with their respective parameters rendered based on the Pydantic schema.

<div style="overflow-x: auto;">
| Tab | Description |
| :--- | :--- |
| **Master** | Central discovery hub: real-time search, tag-based<br>filtering, and interactive path list. |
| **Test** | Bulk testing suite: selective execution,<br>live tracking, and latency metrics. |
| **Analytics** | Visual insights: bar charts for roles, methods,<br>and detailed performance statistics. |
| **Storage** | Session state: direct view and management of<br>JWT tokens and persistent UI selections. |
| **Overrides** | Config preview: displays active `PATH_OVERRIDES`<br>for premium default testing scenarios. |
</div>


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
