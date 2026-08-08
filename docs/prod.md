# 🏭 Production Configuration

## 1. Security Keys (Mandatory)

```dotenv
config_token_secret_key=<long-random-256-bit-secret-key>
config_root_user_password=<strong-root-password>
config_login_password=<strong-login-password>
config_is_enable_signup=0
config_is_debug=0
```

## 2. Disable High-Risk Admin APIs (`is_active: 0`)

In `config_extend.py`, set `"is_active": 0` for sensitive admin endpoints in production:

```python
from config import config_api

# High-risk admin query runners, DB imports, and blob management
disabled_admin_apis = [
    "/admin/sync",
    "/admin/postgres-import",
    "/admin/redis-import",
    "/admin/mongodb-import",
    "/admin/postgres-query-runner-write",
    "/admin/postgres-query-runner-read",
    "/admin/postgres-query-runner-read-export",
    "/admin/postgres-query-generator-ai",
    "/admin/mssql-query-runner-write",
    "/admin/mssql-query-runner-read",
    "/admin/mssql-query-runner-read-export",
    "/admin/clickhouse-query-runner-write",
    "/admin/clickhouse-query-runner-read",
    "/admin/clickhouse-query-runner-read-export",
    "/admin/blob-container-ops",
    "/admin/blob-delete-url",
]

for path in disabled_admin_apis:
    if path in config_api:
        config_api[path]["is_active"] = 0
```

📚 [Back to README](../readme.md)



