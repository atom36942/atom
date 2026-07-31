# 🏭 Production Configuration

Conservative production settings for Atom.

## 1. `config_postgres` control keys

Production-safe values for every `control` key:

```json
{
  "config_postgres": {
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
}
```

---

📚 [Back to README](../readme.md)
