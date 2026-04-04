<details>
<summary>About</summary>

| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend framework to speed up large-scale application development. |
| **Architecture** | Modular architecture combining functional and procedural styles. |
| **Reliability** | Pure functions used to minimize side effects and improve testability. |
| **Production** | Ready to build APIs, background jobs, and integrations quickly. |
| **Efficiency** | Minimal boilerplate so you don’t have to reinvent the wheel each time. |
| **Flexibility** | Non-opinionated and fully flexible to extend. |
| **Tech Stack** | Python, FastAPI, Postgres, Redis, S3, Celery, RabbitMQ, Kafka, Sentry. |

</details>

<details>
<summary>Setup: GitHub SSH & Repository Sync</summary>

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

</details>

<details>
<summary>Setup: Local Deployment</summary>

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

</details>

<details>
<summary>Package Management</summary>

```bash
./venv/bin/pip install fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip install -r requirements.txt
./venv/bin/pip freeze > requirements.txt
```

</details>

<details>
<summary>Setup: Docker Deployment</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```

</details>

<details>
<summary>Setup: Consumer Workers</summary>

```bash
venv/bin/python consumer.py celery
venv/bin/python consumer.py rabbitmq
venv/bin/python consumer.py redis
venv/bin/python consumer.py kafka
```

</details>

<details>
<summary>Brew Setup</summary>

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install python@3.11
brew install postgis
brew install postgresql && brew install redis && brew install rabbitmq && brew tap mongodb/brew && brew install mongodb-community && echo 'export PATH="/opt/homebrew/sbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
brew services start postgresql && brew services start redis && brew services start rabbitmq && brew services start mongodb-community
brew services restart postgresql && brew services restart redis && brew services start rabbitmq && brew services start mongodb-community
brew services stop postgresql && brew services stop redis && brew services stop rabbitmq && brew services stop mongodb-community
brew update && brew upgrade postgresql && brew upgrade redis && brew upgrade rabbitmq && brew upgrade mongodb-community && brew services restart --all
brew services stop --all && brew uninstall --force postgresql && brew uninstall --force redis && brew uninstall --force rabbitmq && brew uninstall --force mongodb-community && rm -rf /opt/homebrew/var/postgres /opt/homebrew/var/db/redis /opt/homebrew/var/lib/rabbitmq /opt/homebrew/var/mongodb && brew cleanup
psql --version && redis-cli --version && rabbitmqctl version && mongosh --version && mongod --version
brew services list
```

</details>


<details>
<summary>Sample Local Env Variable</summary>

```bash
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_mongodb_url=mongodb://localhost:27017
```

</details>


<details>
<summary>Environment Variables</summary>

The application uses a dynamic override system where any variable in `config.py` starting with `config_` can be overridden by a matching environment variable or an entry in a `.env` file. This is handled by `func_config_override_from_env` in `function.py`, which also manages type conversion for booleans (0/1), integers, and JSON objects (for lists or dictionaries).

| Category | Environment Variable | Type | Description |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | `config_postgres_url` | `str` | Connection URL (e.g., `postgresql://user:pass@host/db`). |
| | `config_postgres_min_connection` | `int` | Minimum pool size (Default: 5). |
| | `config_postgres_max_connection` | `int` | Maximum pool size (Default: 20). |
| **Redis / Cache**| `config_redis_url` | `str` | Primary Redis connection string. |
| | `config_redis_url_ratelimiter`| `str` | Redis instance for rate limiting. |
| | `config_redis_cache_ttl_sec` | `int` | TTL for cached API responses in seconds. |
| **Queues** | `config_rabbitmq_url` | `str` | RabbitMQ connection URL. |
| | `config_kafka_url` | `str` | Kafka broker URL. |
| | `config_celery_broker_url`| `str` | Celery broker URL (Defaults to Redis URL). |
| | `config_celery_backend_url`| `str` | Celery result backend URL. |
| **Security** | `config_token_secret_key` | `str` | JWT signing secret. |
| | `config_token_expiry_sec` | `int` | JWT token validity duration in seconds. |
| | `config_cors_origin` | `list` | Allowed CORS origins (JSON array: `["*"]`). |
| **AI Providers** | `config_openai_key` | `str` | OpenAI API key for GPT integrations. |
| | `config_gemini_key` | `str` | Google Gemini API key. |
| **Cloud** | `config_aws_access_key_id` | `str` | AWS access key for S3, SNS, SES. |
| | `config_aws_secret_access_key`| `str` | AWS secret key. |
| | `config_s3_region_name` | `str` | S3 bucket region. |
| | `config_sftp_host` | `str` | SFTP server hostname. |
| | `config_sftp_password` | `str` | SFTP password or key path. |
| **Integrations**| `config_sentry_dsn` | `str` | Sentry DSN for error tracking. |
| | `config_posthog_project_key`| `str` | Posthog project key for analytics. |
| | `config_gsheet_service_account_json_path` | `str` | Path to Google Service Account JSON. |
| **Switches** | `config_is_signup` | `int` | Toggle user signup (1: Enabled, 0: Disabled).|
| | `config_is_log_api` | `int` | Toggle API logging (1: Enabled, 0: Disabled). |
| | `config_is_traceback` | `int` | Toggle Python traceback in responses (1/0). |
| | `config_is_prometheus` | `int` | Toggle `/metrics` prometheus endpoint (1/0). |
| | `config_is_reset_tmp` | `int` | Wipe `./tmp` folder on boot (1/0). |

</details>

<details>
<summary>Repository Map</summary>

A high-level overview of the project architecture and file responsibilities.

| Path | Responsibility | Logic / Pattern |
| :--- | :--- | :--- |
| `main.py` | **Entry Point** | App initialization, middleware pipeline, and lifecycle hooks. |
| `router.py` | **API Endpoints** | Definition of all REST and WebSocket routes with role mapping. |
| `function.py` | **Core Logic** | Pure functional backend logic (Rule 2: No external state). |
| `config.py` | **Global Settings** | Centralized configuration, feature switches, and table schemas. |
| `consumer.py` | **Background Workers** | Entry point for message queue consumers (Celery, Kafka, etc.). |
| `static/` | **Frontend Assets** | HTML, CSS, and JS files served via the `/static/` mount. |
| `tmp/` | **Temporary Storage** | Local workspace for runtime file operations (cleared on boot). |

</details>

<details>
<summary>Service Integrations</summary>

The framework provides pre-configured async clients for a wide range of production services.

| Category | Service Integration | Client / Function Source |
| :--- | :--- | :--- |
| **Databases** | PostgreSQL, Redis, MongoDB | `client_postgres_pool`, `client_redis`, `client_mongodb` |
| **AI / ML** | OpenAI, Google Gemini | `client_openai`, `client_gemini` |
| **Cloud / S3** | Amazon S3, SNS, SES | `client_s3`, `client_sns`, `client_ses` |
| **Messaging** | Celery, Kafka, RabbitMQ, Redis | `client_*_producer` |
| **Analytics** | Posthog, Sentry | `client_posthog`, `func_app_add_sentry` |
| **Utilities** | SFTP, Google Sheets, HTTP | `client_sftp`, `client_gsheet`, `client_http` |

</details>

<details>
<summary>Middleware Pipeline</summary>

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

</details>

<details>
<summary>Security: Route Protection</summary>

Path-based security is enforced automatically by the unified middleware pipeline.

| Prefix Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Identity flows (login, signup, OTP). |
| `/public/` | Public | General data access for non-registered users. |
| `/` | Public | Root indices and documentation. |
| `/my/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/private/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/admin/` | **Role-Based** | Requires token **AND** matching role in `config_api`. |

</details>

<details>
<summary>Security: User State Injection</summary>

Authorized user context and global clients are injected into every request.

| Variable | Key Source | Properties |
| :--- | :--- | :--- |
| **`request.state.user`** | JWT Decoder | `id`, `type`, `role`, `is_active` |
| **`request.app.state`** | Lifespan Hooks | All `client_`, `config_`, and `func_` singletons. |

</details>

<details>
<summary>PostgreSQL: System Initialization</summary>

The schema is managed through administrative endpoints and automated startup checks.

| Feature | Logic Source | Behavior |
| :--- | :--- | :--- |
| **Schema Init** | `/admin/postgres-init` | Triggers `func_postgres_init` to setup extensions and tables. |
| **Root User** | `func_postgres_init_root_user` | Automatically creates the first admin user on boot. |
| **Auto-Migration** | `func_postgres_create` | Creates tables on-the-fly if missing during buffer flushes. |

</details>

<details>
<summary>PostgreSQL: Advanced Read Filters</summary>

The generic reader support complex query logic via URL parameters.

| Category | Filter Pattern | Behavior |
| :--- | :--- | :--- |
| **Spatial** | `location,point,lon\|lat\|min\|max` | Performs bounding box or point radius searches. |
| **JSONB** | `data,contains,key\|value\|type` | Deep-checks JSONB fields for keys or value matches. |
| **Arrays** | `tags,overlap,tagA|tagB` | Matches if any elements overlap shared arrays. |

</details>

<details>
<summary>PostgreSQL: Joins & Aggregations</summary>

These parameters allow for powerful data enrichment and relational fetching without writing custom SQL.

| Parameter | Function | Example |
| :--- | :--- | :--- |
| **`creator_key`** | Injects metadata from the `users` table for the row's `created_by_id`. | `?creator_key=username,email` |
| **`action_key`** | Performs a grouped subquery aggregation (count/sum/min/max) on a target table. | `?action_key=comments,post_id,count,id` |

**Using `creator_key`**
When you provide `creator_key`, the system automatically fetches the specified columns from the `users` table and prefixes them with `creator_` in the response.
- **Query**: `/public/object-read?table=posts&creator_key=username,avatar`
- **Result Object**: `{ "id": 1, "title": "Hello", ..., "creator_username": "atom", "creator_avatar": "url" }`

**Using `action_key`**
The `action_key` is used for 1:N relationship summaries. The syntax is: `{target_table},{target_column},{operation},{source_id_column}`.
- **Scenario**: You want to see how many comments each post has.
- **Query**: `/public/object-read?table=posts&action_key=comments,post_id,count,id`
- **Logic**: It counts rows in the `comments` table where `post_id` matches the post's `id`.
- **Result Object**: `{ "id": 1, "title": "Hello", ..., "comments_count": 5 }`

</details>

<details>
<summary>Redis: Distributed State</summary>

Use Redis for high-performance distributed caching and session state.

| Data Store | Purpose | API / Pattern |
| :--- | :--- | :--- |
| **Redis** | Distributed State | `redis-import-create` / `redis-import-delete`. |

</details>

<details>
<summary>MongoDB: Document Storage</summary>

Use MongoDB for semi-structured document storage and complex JSON objects.

| Data Store | Purpose | API / Pattern |
| :--- | :--- | :--- |
| **MongoDB** | Document Store | `mongodb-import` with hex-to-ObjectId conversion. |

</details>

<details>
<summary>In-Memory: Local State</summary>

Use the built-in in-memory state for temporary, per-node storage.

| Data Store | Purpose | API / Pattern |
| :--- | :--- | :--- |
| **In-Memory** | Local State | `inmemory` mode using `app.state` dictionaries. |

</details>

<details>
<summary>Queues: Async Task Dispatch</summary>

Route high-frequency operations to background queues using a unified producer logic.

| Protocol | Backend | Driver / Client |
| :--- | :--- | :--- |
| **Celery** | Redis | `func_celery_producer` |
| **Kafka** | Event Stream | `func_kafka_producer` |
| **RabbitMQ** | AMQP | `func_rabbitmq_producer` |
| **Redis** | Pub/Sub | `func_redis_producer` |

</details>

<details>
<summary>Admin: Operational Maintenance</summary>

The `/admin/sync` endpoint aligns application state with infrastructure.

| Operation | Logic / Function | Behavior |
| :--- | :--- | :--- |
| **Schema Refresh** | `func_postgres_schema_read` | Re-scans PostgreSQL to update column/table metadata. |
| **Auth Map Sync** | `func_sql_map_column` | Reloads `cache_users_role` and `cache_users_is_active`. |
| **Buffer Flush** | `func_postgres_create` | Forces all pending `buffer` mode operations to commit. |
| **Log Cleanup** | `func_postgres_clean` | executes log pruning based on `retention_day` settings. |

</details>

<details>
<summary>Workers: Consumer Infrastructure</summary>

Dedicated workers for processing long-running or distributed tasks.

| Service | Worker Command | Core Logic |
| :--- | :--- | :--- |
| **Celery** | `python consumer.py celery` | Distributed task execution and scheduling. |
| **RabbitMQ** | `python consumer.py rabbitmq` | Standard AMQP message consumption. |
| **Redis** | `python consumer.py redis` | List or Pub/Sub based worker logic. |
| **Kafka** | `python consumer.py kafka` | High-throughput event stream worker. |

</details>

<details>
<summary>Assets: Content Delivery</summary>

Static and dynamic HTML files are served with recursive search and security checks.

| Feature | Details | Logic |
| :--- | :--- | :--- |
| **Static Mount** | `./static` | Served via the `/static/` URL prefix. |
| **Dynamic Pages** | `/page-{name}` | Recursive HTML search via `func_html_serve`. |
| **Asset Security** | Path Resolution | Isolation from directory traversal attacks. |

</details>

<details>
<summary>Switches: Global Flags</summary>

Application-wide behaviors controlled by `config_is_` boolean flags.

| Switch Name | Default | Execution Logic |
| :--- | :--- | :--- |
| **`config_is_log_api`** | 1 | Toggles non-GET request logging to `log_api`. |
| **`config_is_traceback`** | 1 | Displays full Python errors in API JSON responses. |
| **`config_is_prometheus`** | 0 | Mounts the `/metrics` endpoint for monitoring. |
| **`config_is_reset_tmp`** | 1 | Wipes the `./tmp` folder on every application boot. |

</details>

<details>
<summary>API Tester: Discovery</summary>

The `api.html` dashboard is **fully dynamic**. There is no need to manually register new APIs in the frontend.
- **Spec-Driven**: On every load, the app fetches the latest `openapi.json` from the backend.
- **Zero Maintenance**: New routes added to `router.py` appear automatically with their respective parameters (Headers, Query, Form, Body) rendered based on the Pydantic schema.
- **Custom Defaults**: While discovery is automatic, you can optionally add "premium" defaults (like random UUIDs or specific test IDs) in the `PATH_DEFAULTS` object inside `static/api.html`.

</details>

<details>
<summary>API Tester: Parameter Lifecycle</summary>

The dashboard uses a deterministic, stateless multi-stage population logic to ensure the Bulk Tester always inherits the current UI state. Hardcoded overrides are managed via the `PATH_DEFAULTS` object in `api.html`.

**Automatic Mapping Logic (Two-Layer)**
The dashboard uses a deterministic two-layer logic to map `PATH_DEFAULTS` to the active API runner state:
- **Layer 1: Specification-First**: The system first checks the backend's OpenAPI spec. If a key (e.g., `table`) is explicitly defined as a **Header**, **Query**, **Path**, or **Form** parameter, the default value is mapped directly to that location.
- **Layer 2: Body-Injection**: For `POST`/`PUT` requests related to `object-create`, `object-update`, `ids-delete`, or `signup`, the system performs a fail-safe check. Any key in `PATH_DEFAULTS` that is **not** found in the backend spec is automatically injected into the **JSON Body** to ensure a premium, zero-config testing experience.

**Configuration Samples**
```javascript
const PATH_DEFAULTS = {
  // Auth: Static credentials for common test users
  '/auth/login-password-username': { type: 1, username: 'atom', password: '123' },
  
  // Data: Table-specific query parameters
  '/public/object-read': { table: 'test' },
  
  // Custom: Complex objects and GIS data
  '/my/object-create': { 
    table: 'test', 
    location: 'POINT(17.79 -83.03)', 
    metadata: { "active": true } 
  }
};
```

| Phase | Component | Behavior |
| :--- | :--- | :--- |
| **1. Baseline** | `openapi.json` | Fetched on load to define keys and backend-default values. |
| **2. Defaults** | `PATH_DEFAULTS` | Frontend overrides for specific test cases (Login, Table names, etc). |
| **3. Session State**| `COMMANDS` Array | Live, in-memory array holding the "Ready-to-Ship" data for all APIs. |
| **4. Inheritance** | Bulk API Tester | Iterates through `COMMANDS` and executes requests using the current state. |
| **5. Reset** | Page Refresh | Wipes the `COMMANDS` array—no state is persisted across reloads. |

</details>

<details>
<summary>API Tester: Operational Flow</summary>

- **Direct Sync**: Any edit made in the Manual Runner form is instantly synced to the global `COMMANDS` array.
- **Pure Execution**: The Bulk Tester is a "dumb" runner; it does not generate values but strictly mirrors what is currently in the `COMMANDS` state.
- **Statelessness**: The system is designed to be purely deterministic per-session—if you want to change a test value, edit it in the Manual Runner first.

</details>
