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
<summary>Setup</summary>

### Local Development
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

### Docker Deployment
```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```

### Environment Variables
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
<summary>Project Structure</summary>

### Repository Map
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
<summary>Client Integrations</summary>

### Built-in Service Gallery
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
<summary>Request Lifecycle</summary>

### Middleware Pipeline
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
<summary>Authentication & Security</summary>

### Route Protection
Path-based security is enforced automatically by the unified middleware pipeline.

| Prefix Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Identity flows (login, signup, OTP). |
| `/public/` | Public | General data access for non-registered users. |
| `/` | Public | Root indices and documentation. |
| `/my/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/private/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/admin/` | **Role-Based** | Requires token **AND** matching role in `config_api`. |

### State Injection
Authorized user context and global clients are injected into every request.

| Variable | Key Source | Properties |
| :--- | :--- | :--- |
| **`request.state.user`** | JWT Decoder | `id`, `type`, `role`, `is_active` |
| **`request.app.state`** | Lifespan Hooks | All `client_`, `config_`, and `func_` singletons. |

</details>

<details>
<summary>Database: PostgreSQL</summary>

### System Initialization
The schema is managed through administrative endpoints and automated startup checks.

| Feature | Logic Source | Behavior |
| :--- | :--- | :--- |
| **Schema Init** | `/admin/postgres-init` | Triggers `func_postgres_init` to setup extensions and tables. |
| **Root User** | `func_postgres_init_root_user` | Automatically creates the first admin user on boot. |
| **Auto-Migration** | `func_postgres_create` | Creates tables on-the-fly if missing during buffer flushes. |

### Advanced Read Filters
The generic reader support complex query logic via URL parameters.

| Category | Filter Pattern | Behavior |
| :--- | :--- | :--- |
| **Spatial** | `location,point,lon\|lat\|min\|max` | Performs bounding box or point radius searches. |
| **JSONB** | `data,contains,key\|value\|type` | Deep-checks JSONB fields for keys or value matches. |
| **Arrays** | `tags,overlap,tagA\|tagB` | Matches if any elements overlap shared arrays. |

</details>

<details>
<summary>Database: Redis & MongoDB</summary>

### Hybrid State Management
Use Redis for distributed caching and MongoDB for semi-structured document storage.

| Data Store | Purpose | API / Pattern |
| :--- | :--- | :--- |
| **Redis** | Distributed State | `redis-import-create` / `redis-import-delete`. |
| **MongoDB** | Document Store | `mongodb-import` with hex-to-ObjectId conversion. |
| **In-Memory** | Local State | `inmemory` mode using `app.state` dictionaries. |

</details>

<details>
<summary>Message Queues & Producers</summary>

### Async Task Dispatch
Route high-frequency operations to background queues using a unified producer logic.

| Protocol | Backend | Driver / Client |
| :--- | :--- | :--- |
| **Celery** | Redis | `func_celery_producer` |
| **Kafka** | Event Stream | `func_kafka_producer` |
| **RabbitMQ** | AMQP | `func_rabbitmq_producer` |
| **Redis** | Pub/Sub | `func_redis_producer` |

</details>

<details>
<summary>Admin Sync & Tools</summary>

### Operational Maintenance
The `/admin/sync` endpoint aligns application state with infrastructure.

| Operation | Logic / Function | Behavior |
| :--- | :--- | :--- |
| **Schema Refresh** | `func_postgres_schema_read` | Re-scans PostgreSQL to update column/table metadata. |
| **Auth Map Sync** | `func_sql_map_column` | Reloads `cache_users_role` and `cache_users_is_active`. |
| **Buffer Flush** | `func_postgres_create` | Forces all pending `buffer` mode operations to commit. |
| **Log Cleanup** | `func_postgres_clean` | executes log pruning based on `retention_day` settings. |

</details>

<details>
<summary>Background Workers</summary>

### Consumer Infrastructure
Dedicated workers for processing long-running or distributed tasks.

| Service | Worker Command | Core Logic |
| :--- | :--- | :--- |
| **Celery** | `python consumer.py celery` | Distributed task execution and scheduling. |
| **RabbitMQ** | `python consumer.py rabbitmq` | Standard AMQP message consumption. |
| **Redis** | `python consumer.py redis` | List or Pub/Sub based worker logic. |
| **Kafka** | `python consumer.py kafka` | High-throughput event stream worker. |

</details>

<details>
<summary>Frontend & Static Assets</summary>

### Content Delivery
Static and dynamic HTML files are served with recursive search and security checks.

| Feature | Details | Logic |
| :--- | :--- | :--- |
| **Static Mount** | `./static` | Served via the `/static/` URL prefix. |
| **Dynamic Pages** | `/page-{name}` | Recursive HTML search via `func_html_serve`. |
| **Asset Security** | Path Resolution | Isolation from directory traversal attacks. |

</details>

<details>
<summary>API Controls & Config</summary>

### Global Switches
Application-wide behaviors controlled by `config_is_` boolean flags.

| Switch Name | Default | Execution Logic |
| :--- | :--- | :--- |
| **`config_is_log_api`** | 1 | Toggles non-GET request logging to `log_api`. |
| **`config_is_traceback`** | 1 | Displays full Python errors in API JSON responses. |
| **`config_is_prometheus`** | 0 | Mounts the `/metrics` endpoint for monitoring. |
| **`config_is_reset_tmp`** | 1 | Wipes the `./tmp` folder on every application boot. |

</details>
