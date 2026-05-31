# PostgreSQL Setup & Schema Management

Atom features an automated schema initialization and synchronization engine. This allows you to manage your PostgreSQL database schema entirely through Python configuration dictionaries, without needing manual SQL migration scripts.

## Automated Schema Initialization

During the application startup (defined in `core/app.py` under the `func_lifespan` context manager), Atom automatically checks and initializes the database schema:

```python
# From core/app.py
if client_postgres_pool and app.state.config_is_enable_postgres_init_startup == 1: 
    await app.state.func_postgres_schema_init(
        client_postgres_pool=client_postgres_pool, 
        client_password_hasher=client_password_hasher, 
        config_postgres=app.state.config_postgres, 
        config_root_user_password=app.state.config_root_user_password
    )
```

If `config_is_enable_postgres_init_startup` is set to `1` (which is the default in `core/config.py`), the `func_postgres_schema_init` function will execute. It connects to the database, creates required extensions, creates missing tables, and synchronizes columns, indexes, and constraints to match your configuration.

## Modifying the Schema (`config_postgres`)

The entire database structure is defined in the `config_postgres` dictionary within `core/config.py`. 

To create a new table or modify an existing one, you simply update the `table` key inside `config_postgres`.

> **Note on the `test` table:** If you look at `config.py`, you will notice a `test` table defined under `config_postgres["table"]`. This table is specifically included as a comprehensive example that showcases all possible column settings, data types, and constraint combinations available in Atom.

### Example: Defining a Table

```python
# Inside core/config.py
config_postgres = {
    "extension": ["postgis", "pg_trgm", "btree_gin"],
    "table": {
        "your_new_table": [
            {"name": "id", "datatype": "bigserial", "is_primary": 1},
            {"name": "created_at", "datatype": "timestamptz", "default": "now()", "index": "btree(created_at)"},
            {"name": "title", "datatype": "text", "is_mandatory": 1, "index": "gin(title)"},
            {"name": "status", "datatype": "smallint", "default": 1},
            {"name": "price", "datatype": "numeric(10,2)", "check": "price > 0"}
        ],
        # ... other tables ...
    }
}
```

### Supported Column Attributes

When defining a column in a table list, you can use the following attributes:

- `name`: The name of the column (string).
- `datatype`: The PostgreSQL data type (e.g., `"bigserial"`, `"timestamptz"`, `"text"`, `"boolean"`, `"jsonb"`, `"integer[]"`).
- `is_primary`: Set to `1` to designate the primary key.
- `is_mandatory`: Set to `1` to enforce a `NOT NULL` constraint.
- `default`: The default SQL value (e.g., `"now()"`, `0`, `False`).
- `unique`: Defines a unique constraint. You can create composite unique constraints by separating column names with commas (e.g., `"username,type"`).
- `check`: Defines a SQL check constraint (e.g., `"rating >= 0 AND rating <= 5"`).
- `index`: Defines the index type and columns (e.g., `"btree(status)"`, `"gin(metadata)"`).
- `regex`: A regex pattern the data must match before insertion.
- `in`: A tuple of allowed values (e.g., `(1, 2, 3)`).

### Applying Changes
Because of the auto-schema engine, once you update `config.py` and restart the FastAPI server, Atom will automatically detect the changes and alter the PostgreSQL tables to match the new definitions.

## Integer to Text Mapping

For columns storing categorical states (like `status`, `type`, or `role`), Atom uses small integers in the database for optimization. The dictionary `config_column_int_mapping` in `config.py` acts as the single source of truth for converting these integers into human-readable text representations across the application.

```python
# Example from config.py
config_column_int_mapping = {
    "status": {
        "job": {1: "Draft", 2: "Approval Pending", 3: "Approved"},
        # ...
    },
    # ...
}
```
This mapping ensures consistency without requiring repetitive ENUM types or joins in SQL queries.

## Schema Control Flags (`config_postgres["control"]`)

Atom provides explicit controls over how the automated schema synchronizer behaves, particularly regarding destructive operations. These are defined in the `control` dictionary inside `config_postgres`.

```python
"control": {
    "is_enable_drop_column": 1,
    "is_enable_truncate": 1,
    "is_enable_autovacuum_optimize": 1,
    "actor_tracking_column": {
        "deleted_at": "deleted_by_id",
        "deactivated_at": "deactivated_by_id"
    },
    # ...
}
```

- **Safety Toggles**: Flags like `is_enable_drop_column` or `is_enable_drop_table` control whether the synchronizer is allowed to delete existing schema entities if they are removed from your Python config. **In production environments, these should typically be set to `0`** to prevent accidental data loss.
- **Actor Tracking**: The `actor_tracking_column` automatically links action timestamps (like `deleted_at`) to the user ID who performed the action (`deleted_by_id`).
- **Optimization**: `is_enable_autovacuum_optimize` instructs the system to automatically apply optimized autovacuum settings to heavily utilized tables.

## Custom SQL Indexes

While basic indexes are generated via the column attributes (e.g., `"index": "btree(status)"`), more advanced or conditional indexes can be defined using raw SQL in `config_postgres["sql"]["index"]`.

```python
"sql": {
    "index": {
        "idx_users_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_users_deactivated_at_not_null ON users (id) WHERE deactivated_at IS NOT NULL",
        "idx_users_active_email_unique": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_active_email_unique ON users (email) WHERE deactivated_at IS NULL"
    }
}
```

This is heavily utilized for partial indexes, ensuring uniqueness constraints are only applied to active users (ignoring softly-deleted ones) and speeding up queries by only indexing relevant row subsets.

## Table Lifecycle & Buffering (`config_table`)

Independent of the schema structure, Atom defines operational behavior for individual tables in the `config_table` dictionary:

```python
config_table = {
    "log_api": {"retention_day": 30, "buffer_limit": 10},
    "test": {"buffer_limit": 10}
}
```

- **`retention_day`**: Instructs background workers to automatically prune records older than the specified number of days. This is highly useful for logs, OTPs, and temporary caching tables to prevent boundless storage growth.
- **`buffer_limit`**: Defines memory buffering size for high-frequency write tables. Instead of executing individual `INSERT` queries for high-throughput tables like `log_api`, Atom buffers the objects in memory and flushes them to the database in bulk either when the buffer limit is reached, or via the `pulse_flush` background loop.
