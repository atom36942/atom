# ⚙️ Configuration Reference

Atom is driven by `config.py` — a single file of plain Python values loaded onto `app.state` at startup.

---

## How config is loaded & overridden

Config values are resolved in three tiers (later wins):

1. **`config.py`** — Shipped defaults.
2. **Environment variables / `.env`** — `config_*` names in `.env` automatically override defaults with automatic type casting (booleans, ints, JSON arrays/dicts).
3. **`config_extend.py`** — Drop-in module (git-ignored, survives `sync.py`) for code-level overrides and schema extensions. See [extend.md](extend.md).

> **Rule of Thumb**: Use `.env` for secrets, credentials, and environment flags; use `config_extend.py` for structural changes (tables, custom route policies).

Boolean defaults remain booleans when overridden from `.env`. Use case-insensitive `true` or `false` as the standard form:

```dotenv
config_is_signup=true
config_is_debug=false
```

The loader also accepts `1`/`0`, `yes`/`no`, and `on`/`off`. Any other value raises a startup error instead of silently choosing a value. In Python configuration such as `config.py` or `config_extend.py`, always use `True` and `False`.

---

## Single Configuration Keys

All scalar and list settings in `config.py` grouped by section:

### Integrations

Disabled (`None`) by default; activated automatically when connection credentials are set.

| Key | Usage |
|---|---|
| `config_postgres_url` | Primary PostgreSQL connection string DSN |
| `config_postgres_url_dict` | Runtime mapping of named PostgreSQL pools (populated via `config_postgres_url_<name>`) |
| `config_redis_url` | Main Redis URL for response caching & imports |
| `config_redis_url_user_state` | Dedicated Redis for user state/role/deactivation lookups |
| `config_redis_url_ratelimiter` | Dedicated Redis for distributed rate limiter counters |
| `config_redis_url_queue` | Redis URL used as background job queue producer |
| `config_mongodb_url` | MongoDB (Motor) connection string DSN |
| `config_mssql_url` | MSSQL connection pool connection string |
| `config_clickhouse_url` | ClickHouse async DSN for query runner |
| `config_google_login_client_id` | Google OAuth Client ID for token verification |
| `config_openai_key` | OpenAI API key |
| `config_gemini_key` | Google Gemini API key |
| `config_posthog_project_host` | PostHog analytics host URL |
| `config_posthog_project_key` | PostHog analytics project key |
| `config_sentry_dsn` | Sentry DSN for error tracking |
| `config_fast2sms_url` | Fast2SMS gateway URL |
| `config_fast2sms_key` | Fast2SMS API key |
| `config_resend_url` | Resend email API URL |
| `config_resend_key` | Resend email API key |
| `config_sftp_host` | SFTP server hostname |
| `config_sftp_port` | SFTP server port |
| `config_sftp_username` | SFTP server username |
| `config_sftp_password` | SFTP server password |
| `config_aws_access_key_id` | AWS Access Key ID |
| `config_aws_secret_access_key` | AWS Secret Access Key |
| `config_aws_s3_region_name` | AWS S3 region name |
| `config_aws_sns_region_name` | AWS SNS region name |
| `config_aws_ses_region_name` | AWS SES region name |
| `config_azure_account_name` | Azure Storage account name |
| `config_azure_account_key` | Azure Storage account key |
| `config_azure_email_connection_string` | Azure email connection string |
| `config_kafka_url` | Apache Kafka broker URL |
| `config_kafka_username` | Kafka SASL username |
| `config_kafka_password` | Kafka SASL password |
| `config_rabbitmq_url` | RabbitMQ broker URL |
| `config_celery_url` | Celery broker/backend URL |

### System & Security

| Key | Usage |
|---|---|
| `config_root_user_password` | Password for seeded root admin (hashed at startup) |
| `config_login_password` | Default fallback login password for test environments |
| `config_token_secret_key` | HMAC secret key for signing/verifying JWT tokens *(Must change)* |
| `config_root_html_path` | Path to static HTML file served at `/` (`static/api.html`) |
| `config_is_user_delete` | Boolean toggle for the user hard-deletion flow |
| `config_is_postgres_schema_init` | Boolean toggle for database schema initialization on startup |
| `config_is_signup` | Boolean toggle for public user signup routes in `router/auth.py` |
| `config_is_otp_require_users_update` | Boolean requiring OTP verification when updating user contact details |
| `config_is_read_only` | Boolean system-wide read-only mode toggle |
| `config_is_debug` | Boolean FastAPI debug-mode toggle (`False` in production) |
| `config_postgres_db_log_api` | Named Postgres pool key for API logging (`None` = primary pool) |

### Limits, OTP & Auth

| Key | Usage |
|---|---|
| `config_postgres_pool_min_size` | Minimum connections per PostgreSQL pool (default: `5`) |
| `config_postgres_pool_max_size` | Maximum connections per PostgreSQL pool (default: `20`) |
| `config_otp_length` | Digit length generated for OTP codes (default: `6`) |
| `config_otp_expiry_sec` | Expiry window for OTP codes in seconds (default: `600`) |
| `config_access_token_expires_sec` | JWT Access Token lifetime in seconds |
| `config_refresh_token_expires_sec` | JWT Refresh Token lifetime in seconds |
| `config_blob_limit_size_kb` | Maximum file upload size in KB (default: `500`) |
| `config_blob_limit_upload` | Maximum files allowed per upload request (default: `100`) |
| `config_blob_expire_sec_upload` | Presigned upload URL lifetime in seconds (`3600`) |
| `config_blob_expire_sec_preview` | Presigned preview URL lifetime in seconds (`360000`) |
| `config_buffer_limit_default` | In-memory buffer size before flushing rows to Postgres (`100`) |
| `config_postgres_buffer_flush_auto_sec` | Timer interval in seconds to auto-flush write buffers (`60`) |
| `config_inmemory_cache_cleanup_auto_sec` | Timer interval in seconds to purge expired cache entries (`300`) |
| `config_batch_item_limit` | Maximum objects allowed per batch CRUD request (`1000`) |
| `config_sql_read_limit_default` | Default page size for object read queries (`100`) |
| `config_sql_read_limit_max` | Hard cap limit for object read page size (`10000`) |
| `config_sql_read_relation_fetch_limit_max` | Maximum rows fetched per joined relation (`100`) |
| `config_query_runner_read_limit` | Maximum row cap for admin SQL query runner (`5000`) |
| `config_query_runner_export_limit` | Maximum row cap for admin CSV query exports (`50000`) |
| `config_allowed_users_role` | Valid role numbers accepted at signup/login (`[1, 2, 3, 4, 5]`) |
| `config_redis_cache_ttl_sec` | TTL for Redis-cached role/user status lookups (`3600`) |
| `config_users_delete_data_retention_day` | Retention grace period in days before soft-deleted users are purged (`30`) |

### CORS

| Key | Usage |
|---|---|
| `config_cors_allow_origins` | List of allowed CORS origin URLs (`[]`) |
| `config_cors_allow_origin_regex` | Regex pattern matching allowed CORS origins (`.*`) |
| `config_cors_allow_methods` | Allowed HTTP methods for CORS (`["*"]`) |
| `config_cors_allow_headers` | Allowed request headers for CORS (`["*"]`) |
| `config_cors_expose_headers` | Exposed headers for CORS (`["*"]`) |
| `config_cors_allow_credentials` | Allow cookies/credentials in CORS requests (`True`) |

### Table Access Control

| Key | Usage |
|---|---|
| `config_table_sensitive` | Protected tables exempted from bulk cleanup/deletion scripts |
| `config_table_my_create_disabled` | Tables refused on user `/my/object-create` endpoint |
| `config_table_my_delete_all_enabled` | Tables supporting `/my/object-delete-all` for row owners |
| `config_table_my_delete_all_received_enabled` | Tables supporting delete-all-received (messages, notifications) |
| `config_table_public_create_enabled` | Tables accessible on unauthenticated public create route |
| `config_table_public_read_enabled` | Tables accessible on unauthenticated public read route |
| `config_table_private_read_enabled` | Tables accessible on authenticated private read route |

### Column Rules

| Key | Usage |
|---|---|
| `config_column_token_encode` | User columns encoded into JWT claims (`id`, `role`, `username`, etc.) |
| `config_column_ownership` | Column names indicating row ownership (`created_by_id`, `user_id`) |
| `config_column_admin` | Server-managed columns blocked from user mutation (`created_at`, `role`, etc.) |
| `config_column_admin_users` | Admin-only restricted columns for `users` table (`role`) |
| `config_column_single_update` | Columns requiring single-field update requests (`password`, `email`, etc.) |

### Service Registries

| Key | Usage |
|---|---|
| `config_queue_services` | Registered background queue providers (`redis`, `rabbitmq`, `kafka`, `celery`) |
| `config_blob_services` | Registered blob storage providers (`s3`, `azure`) |
| `config_email_services` | Registered email providers (`ses`, `resend`, `azure`) |
| `config_mobile_services` | Registered SMS providers (`sns`, `fast2sms`) |
| `config_ai_services` | Registered AI service providers (`gemini`, `openai`) |

---

## Dict Configurations

Detailed breakdown of all dictionary settings in `config.py`.

### `config_api`

Per-endpoint security and execution policy table.

#### Policy Fields (Nested Keys)

| Key | Type / Value | Description & Usage |
|---|---|---|
| `id` | `int` | Unique numeric identifier for the endpoint |
| `is_active` | `bool` | Toggles endpoint availability (`False` disables the endpoint via middleware) |
| `is_token` | `bool` | `True` requires a valid JWT access token; `False` allows public unauthenticated access |
| `user_check_role` | `{"mode": "...", "roles": [...]}` | Restricts access to users with listed role numbers |
| `user_check_deactivated` | `{"mode": "..."}` | Blocks request if user has `deactivated_at` timestamp set |
| `user_check_deleted` | `{"mode": "..."}` | Blocks request if user has `deleted_at` timestamp set |
| `rate_limit` | `{"mode": "...", "limit": N, "window_sec": S}` | Limits requests to `limit` per `window_sec` seconds |
| `cache` | `{"mode": "...", "ttl_sec": S, "is_per_user": bool}` | Caches responses for `ttl_sec` seconds (`is_per_user: True` isolates entries per user) |

#### Inspection Modes (`mode` Nested Key)

| Mode Value | Data Source | Characteristics & Best Use Case |
|---|---|---|
| `token` | JWT Payload | Fastest (zero DB lookup); best for stable claims |
| `inmemory` | Redis / Memory Cache | High speed; subject to `config_redis_cache_ttl_sec` TTL |
| `realtime` | Live PostgreSQL Query | Guaranteed freshness; best for critical admin/delete ops |

---

### `config_postgres`

Declarative schema initialization and migration configuration.

#### Top-Level Dict Keys

| Key | Type | Usage |
|---|---|---|
| `extension` | `list[str]` | PostgreSQL extensions to install on startup (`["postgis", "pg_trgm", "btree_gin"]`) |
| `table` | `dict[str, list[dict]]` | Table schemas defined as list of column specification dicts |
| `control` | `dict` | Safety flags and auto-migration control settings |
| `sql` | `dict[str, str]` | Raw custom SQL executed during schema startup initialization |

#### Table Column Specification Dict Keys (`config_postgres["table"][<table_name>]`)

| Column Spec Key | Type | Usage & Description |
|---|---|---|
| `name` | `str` | Column name (first column must be `id` primary key) |
| `datatype` | `str` | PostgreSQL data type (e.g. `bigint`, `timestamptz`, `text`, `jsonb`, `geography`) |
| `identity` | `str` | Identity column strategy (`"always"` or `"by_default"`) |
| `is_primary` | `bool` | `True` designates the identity primary-key column |
| `is_mandatory` | `bool` | `True` adds a `NOT NULL` constraint |
| `default` | `str` / `int` | Default value/expression (e.g. `"now()"`, `1`) |
| `unique` | `str` | Unique constraint (`"code,type"` for composite; `"code,type\|code,slug"` for multiple) |
| `check` | `str` | SQL `CHECK` clause (e.g. `"rating >= 0 AND rating <= 10"`) |
| `regex` | `str` | Validation pattern checked on write by `func_regex_check` |
| `index` | `str` | Index spec (`"btree(email)"`, `"gin_trgm(title)"`, `"gist(coordinate)"`) |
| `in` | `tuple` | Allowed integer value set (e.g. `(1, 2, 3, 4)`) |
| `old` | `str` | Renames existing column from `old` to `name` safely without dropping data |

#### `control`

Auto-migration and safety guards in `config_postgres["control"]`.

| Control Key | Default | Usage & Description |
|---|---|---|
| `is_updated_at_set` | `True` | Auto-attaches trigger to maintain `updated_at` column on record update |
| `is_protected_delete_disabled` | `True` | Prevents deletion of rows where `is_protected = true` |
| `is_truncate_table` | `False` | Controls whether table truncation is permitted during startup schema init |
| `is_log_users_password` | `True` | Automatically records password changes into `log_users_password` |
| `is_log_users_delete` | `True` | Automatically logs user soft/hard deletion actions into `log_users_delete` |
| `is_root_user_create` | `True` | Automatically seeds initial root admin user on startup |
| `is_root_user_delete_disabled` | `True` | Protects root admin user account from deletion |
| `table_row_delete_disable` | `["users", ...]` | Tables where row deletion is entirely prohibited |
| `table_row_delete_disable_bulk` | `[["*", 1000]]` | Caps on maximum rows allowed in a single bulk delete operation |

---

### `config_sql`

Pre-cached SQL queries executed at startup.

| Key | Usage / Description |
|---|---|
| `config` | Selects key/value pairs from `config` table into `cache_config` |
| `users_role` | Pre-fetches user role lookup map for middleware verification |
| `users_deactivated` | Pre-fetches user `deactivated_at` timestamps for middleware checks |
| `users_deleted` | Pre-fetches user `deleted_at` timestamps for middleware checks |
| `profile_metadata` | Profile metadata queries |

---

### `config_table`

Per-table operational settings map.

| Table Key | Nested Key | Type | Usage & Description |
|---|---|---|---|
| `<table_name>` | `buffer_limit` | `int` | Overrides `config_buffer_limit_default` write-buffer threshold |
| `<table_name>` | `retention_day` | `int` | Days to retain records before cleanup workers purge expired rows |

---

### `config_regex`

Write-time regex validation rules enforced by `func_regex_check`.

| Field Name | Pattern (Index 0) | Error Message (Index 1) |
|---|---|---|
| `username` | `^(?=.{1,120}\Z)\S+\Z` | Username must be 1-120 characters and contain no spaces |
| `password` | `^(?=.{6,120}\Z)\S+\Z` | Password must be 6-120 characters and contain no spaces |

---

### `config_dropdown`

Enumerated option lists for frontend UI dropdowns exposed via `/info`.

| Dropdown Key | Values | Usage |
|---|---|---|
| `gender` | `["male", "female"]` | Option list for gender dropdown selector |

---

### `config_column_int_mapping`

Human-readable label mapping for integer-coded database columns.

| Table / Column Key | Integer Code | String Label / Meaning |
|---|---|---|
| `log_users_delete.worker_status` | `None` | Pending |
| `log_users_delete.worker_status` | `1` | Processing |
| `log_users_delete.worker_status` | `2` | Completed |
| `log_users_delete.worker_status` | `3` | Failed |
| `log_users_delete.worker_status` | `4` | Dead |
| `log_users_delete.type` | `1` | User Soft Deleted |
| `log_users_delete.type` | `2` | User Restored |
| `log_users_delete.type` | `3` | User Hard Deleted |
| `blob.type` | `1` | File |
| `blob.type` | `2` | Presigned Url |

Mappings use the lookup order `config_column_int_mapping[table][column][value]`.

---

📚 [Back to README](../readme.md)
