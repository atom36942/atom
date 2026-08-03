# 🏭 Production Configuration

Conservative production settings for Atom.

## 1. `config_postgres` control keys

Copy and paste this `control` object:

```json
{
  "control": {
    "is_enable_autovacuum_optimize": 1,
    "is_enable_updated_at_set": 1,
    "is_enable_is_protected_delete_disable": 1,
    "is_enable_drop_schema": 0,
    "is_enable_drop_table": 0,
    "is_enable_truncate_table": 0,
    "is_enable_drop_column": 0,
    "is_enable_drop_column_mismatch": 0,
    "is_enable_log_users_password": 1,
    "is_enable_log_users_delete": 1,
    "is_enable_root_user_create": 0,
    "is_enable_root_user_delete_disable": 1,
    "is_enable_users_role_delete_disable_hard": 1,
    "is_enable_users_role_delete_disable_soft": 1,
    "table_row_delete_disable_all": [
      "users",
      "config",
      "log_users_password",
      "log_users_delete"
    ],
    "table_row_delete_disable_bulk": [
      ["*", 1000]
    ]
  }
}
```

## 2. Required production `.env`

Replace the placeholder secrets and add these values to `.env`:

```dotenv
config_root_user_password=<strong-root-password>
config_login_password=<strong-login-password>
config_token_secret_key=<long-random-token-secret>
config_root_html_path=static/api.html
config_is_enable_user_delete=0
```

## 3. Recommended production `.env`

```dotenv
config_is_debug=0
config_is_enable_signup=0
config_cors_allow_origins=["https://app.example.com"]
config_access_token_expires_sec=900
config_refresh_token_expires_sec=2592000
config_table_public_create_enable=[]
config_table_public_read_enable=[]
config_table_my_delete_all_enable=[]
config_table_my_delete_all_received_enable=[]
config_table_my_create_disable=["users","log_api","log_users_password","otp","spatial_ref_sys"]
config_table_sensitive=["spatial_ref_sys","users","log_users_delete"]
```

### Critical table-access settings

Review these values for the production schema before deployment:

- `config_table_public_create_enable`: controls anonymous writes through `/public/object-create`. Keep it empty unless a table is explicitly designed and validated for untrusted public submissions.
- `config_table_public_read_enable`: controls anonymous reads through `/public/object-read` and `/public/table-groupby`. List only intentionally public tables, for example `["public_catalog"]`.
- `config_table_my_delete_all_enable` and `config_table_my_delete_all_received_enable`: enable bulk deletion endpoints for the listed tables. Keep them empty unless the application requires those operations.
- `config_table_my_create_disable`: prevents authenticated users from creating rows directly in protected tables. Preserve the security-sensitive defaults and add application-specific protected tables.
- `config_table_sensitive`: protects listed tables from cleanup and deletion scripts. Add any application tables that must never be removed by bulk maintenance.

> **Production warning:** Never use `["*"]` for a public allow-list unless every table is safe for anonymous access. Start with empty allow-lists and add tables individually after reviewing their columns, ownership rules, and stored data.

---

📚 [Back to README](../readme.md)
