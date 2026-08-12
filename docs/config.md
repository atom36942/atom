# ⚙️ Configuration Reference

Atom is driven by `config.py` — a single file of plain Python values loaded onto `app.state` at startup.

---

## How config is loaded & overridden

Config values are resolved in three tiers (later wins):

1. **`config.py`** — Shipped defaults.
2. **Environment variables / `.env`** — `config_*` names in `.env` automatically override defaults with automatic type casting (booleans, ints, JSON arrays/dicts).
3. **`config_extend.py`** — Drop-in module (git-ignored, survives `sync.py`) for code-level overrides and schema extensions. See [extend.md](extend.md).

> **Rule of Thumb**: Use `.env` for secrets, credentials, and environment flags; use `config_extend.py` for structural changes (tables, custom route policies).

---

## Core Settings

Set these in `.env` or `config_extend.py` to configure your application:

### Integrations
Integrations default to `None` (disabled) and activate automatically when connection credentials are set:
- **Databases**: `config_postgres_url`, `config_redis_url`, `config_mongodb_url`, `config_mssql_url`, `config_clickhouse_url`.
- **Cloud & Storage**: `config_aws_access_key_id` / `_secret_access_key` / `_s3_region_name`, `config_azure_account_name` / `_account_key`.
- **Queues**: `config_kafka_url`, `config_rabbitmq_url`, `config_celery_url`.
- **Services & AI**: `config_openai_key`, `config_gemini_key`, `config_sentry_dsn`, `config_posthog_project_key`, `config_resend_key`, `config_fast2sms_key`.

### System & Security
- `config_token_secret_key`: HMAC key for signing JWTs *(change in production)*.
- `config_root_user_password`: Default root admin password *(change in production)*.
- **Flags**: `config_is_signup`, `config_is_postgres_schema_init`, `config_is_user_delete`, `config_is_debug`.

### OTP & Auth Limits
- `config_otp_length` (default `6`) & `config_otp_expiry_sec` (default `600`s).
- `config_access_token_expires_sec` & `config_refresh_token_expires_sec`.
- `config_postgres_pool_min_size` (`5`) & `config_postgres_pool_max_size` (`20`).

---

## Structured Configs

### `config_api`
Per-endpoint middleware policy dict mapping paths to authentication, role, rate-limiting, and caching rules:

```python
"/admin/object-delete": {
    "id": 5,
    "is_token": 1,
    "user_check_role": {"mode": "realtime", "roles": [1]},
    "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60},
}
```

- **Policy Keys**: `is_active`, `is_token`, `user_check_role`, `user_check_deactivated`, `user_check_deleted`, `rate_limit`, `cache`.
- **Check Modes**: `token` (reads JWT claim), `inmemory` (Redis/process cache), `realtime` (live DB query on every request).

### `config_postgres`
Declarative database schema applied at startup when `config_is_postgres_schema_init = 1`:
- **`extension`**: PostgreSQL extensions (`pg_trgm`, `postgis`, `btree_gin`).
- **`table`**: Dict of `table_name -> [column specs]` defining data types, primary keys, indexes, default expressions, unique/check constraints, and `old` column names for safe renames.

#### `control`
Auto-migration safety flags inside `config_postgres["control"]`:
- `is_truncate_table`: Allow table truncation during init (`0`).
- `is_updated_at_set`: Auto-update `updated_at` timestamps via triggers (`1`).
- `is_root_user_create`: Seed initial root admin user (`1`).
- `table_row_delete_disable_all`: Tables where row deletion is entirely blocked.
- `table_row_delete_disable_bulk`: Limits for bulk row deletions.

### `config_table` & `config_sql`
- **`config_table`**: Per-table operational rules (e.g. `buffer_limit`, `retention_day`).
- **`config_sql`**: Startup SQL queries cached in memory for fast middleware lookups.

### Rules & Registries
- **Table Access Control**: Lists gating generic CRUD endpoints (`config_table_sensitive`, `config_table_public_read_enabled`, `config_table_my_create_disabled`).
- **Column Rules**: `config_column_admin`, `config_column_ownership`, `config_column_single_update`.
- **Service Registries**: Supported service providers (`config_queue_services`, `config_blob_services`, `config_email_services`, `config_ai_services`).

---

📚 [Back to README](../readme.md)
