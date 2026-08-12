# 🏭 Production Configuration

## 1. Security Keys (Mandatory)

```dotenv
config_token_secret_key=<long-random-256-bit-secret-key>
config_root_user_password=<strong-root-password>
config_login_password=<strong-login-password>
config_is_signup=false
config_is_debug=false
```

## 2. Disable High-Risk Admin APIs

Set `"is_active": False` in `config_api` for these high-risk write endpoints in production:

- `/admin/sync`
- `/admin/postgres-import`
- `/admin/redis-import`
- `/admin/mongodb-import`
- `/admin/postgres-query-runner-write`
- `/admin/mssql-query-runner-write`
- `/admin/clickhouse-query-runner-write`
- `/admin/blob-container-ops`
- `/admin/blob-delete-url`

📚 [Back to README](../readme.md)



