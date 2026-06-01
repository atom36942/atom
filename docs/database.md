# Database Operations

This document details how to interact with PostgreSQL using Atom's core monolithic database functions. Rather than writing raw SQL, developers should use the functions provided in `core/function.py` to ensure consistency, security, and integration with the auto-schema engine.

## 1. Overview

The data access layer consists of generic asynchronous CRUD functions. All database functions require dependency injection (e.g., passing `client_postgres_pool`, `cache_postgres_schema`, and relevant configuration dictionaries). These are typically accessed via `request.app.state`.

---

## 2. Reading Data (`func_postgres_read`)

The `func_postgres_read` function retrieves data dynamically. It supports advanced filtering, pagination, ordering, specific column selection, and relation fetching.

### Basic Usage

```python
results = await app_state.func_postgres_read(
    client_postgres_pool=app_state.client_postgres_pool,
    client_password_hasher=app_state.client_password_hasher,
    func_postgres_serialize=app_state.func_postgres_serialize,
    func_postgres_where_build=app_state.func_postgres_where_build,
    func_postgres_relation=app_state.func_postgres_relation,
    cache_postgres_schema=app_state.cache_postgres_schema,
    config_relation_fetch_limit_max=app_state.config_relation_fetch_limit_max,
    table="users",
    filter=[["status", "=", 1]],  # List of filter conditions
    limit=10,
    page=1,
    order="id DESC",
    column="id, email, created_at",
    relation=[]
)
```

### Filtering (`func_postgres_where_build`)
The `filter` argument expects a list of conditions, typically provided by the client as JSON.
Format: `[["column_name", "operator", "value"], ...]`.
Supported operators include `=`, `>`, `<`, `>=`, `<=`, `LIKE`, `ILIKE`, `IN`.

### Relation Fetching (`func_postgres_relation`)
The `relation` argument allows fetching linked data natively, eliminating the need for complex SQL `JOIN` statements in your router. 
Format: `[{"table": "profile", "foreign_key": "user_id", "type": "single"}]`.

---

## 3. Creating Data (`func_postgres_create`)

The `func_postgres_create` handles both single and bulk insertions. It also supports buffering for high-throughput tables.

### Basic Usage

```python
inserted_data = await app_state.func_postgres_create(
    client_postgres_pool=app_state.client_postgres_pool,
    client_postgres_conn=None, # Provide an active connection if inside a transaction
    client_password_hasher=app_state.client_password_hasher,
    func_postgres_serialize=app_state.func_postgres_serialize,
    func_regex_check=app_state.func_regex_check,
    cache_postgres_schema=app_state.cache_postgres_schema,
    cache_postgres_buffer_create=app_state.cache_postgres_buffer_create,
    config_regex=app_state.config_regex,
    config_table=app_state.config_table,
    config_obj_list_limit=app_state.config_obj_list_limit,
    config_buffer_limit=app_state.config_buffer_limit,
    mode="insert", # Use "buffer" for background memory buffering
    table="candidate",
    obj_list=[{"name": "John", "email": "john@example.com"}]
)
```

### Modes
- `"insert"`: Executes a direct PostgreSQL `INSERT` statement.
- `"buffer"`: Pushes the objects into the memory buffer (`cache_postgres_buffer_create`). The background worker (`pulse_flush`) will execute a bulk insert when the time interval or `buffer_limit` is reached.

---

## 4. Updating Data (`func_postgres_update`)

The `func_postgres_update` modifies existing records. Every object in the `obj_list` must contain an `id` primary key.

### Basic Usage

```python
updated_data = await app_state.func_postgres_update(
    client_postgres_pool=app_state.client_postgres_pool,
    client_postgres_conn=None,
    client_password_hasher=app_state.client_password_hasher,
    func_postgres_serialize=app_state.func_postgres_serialize,
    func_regex_check=app_state.func_regex_check,
    cache_postgres_schema=app_state.cache_postgres_schema,
    config_regex=app_state.config_regex,
    config_table=app_state.config_table,
    config_obj_list_limit=app_state.config_obj_list_limit,
    table="job",
    obj_list=[{"id": 5, "status": 2}],
    created_by_id=request.state.user.get("id") # Used for automated tracking columns if configured
)
```

---

## 5. Deleting Data (`func_postgres_delete`)

The `func_postgres_delete` handles soft and hard deletions based on your schema controls.

### Basic Usage

```python
deleted_count = await app_state.func_postgres_delete(
    client_postgres_pool=app_state.client_postgres_pool,
    client_postgres_conn=None,
    cache_postgres_schema=app_state.cache_postgres_schema,
    config_obj_list_limit=app_state.config_obj_list_limit,
    table="candidate",
    ids=[10, 11, 12],
    created_by_id=request.state.user.get("id"),
    config_is_enable_user_delete=app_state.config_is_enable_user_delete
)
```

If the table contains a `deleted_at` column, this function performs a soft delete by setting the timestamp. Otherwise, it executes a hard `DELETE` query.
