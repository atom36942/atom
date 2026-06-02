# Frequently Asked Questions (FAQ)

---

### Q: What is the use of the `is_background` parameter?

**A:** Passing `is_background=1` as a query parameter tells the application to process the API request asynchronously in the background. The server immediately returns a generic response, freeing up the client while the actual heavy operation runs silently. 

**Example:**
- **Synchronous:** `POST /my/message-delete-bulk?mode=all`
- **Background:** `POST /my/message-delete-bulk?mode=all&is_background=1`

---

### Q: What is the use of the `is_disable_cache` parameter?

**A:** Passing `is_disable_cache=1` as a query parameter forces the application to bypass any cached responses for that API endpoint. Instead of returning a stored response, the server executes the full API logic (e.g., querying the database fresh). This is extremely useful when you need real-time data or want to ensure you aren't seeing stale cached content.

**Example:**
- **Cached (Default behavior):** `GET /public/object-read` (May return a cached response if recently requested)
- **Bypass Cache:** `GET /public/object-read?is_disable_cache=1` (Always fetches fresh data from the database)

---

### Q: How do I filter records in `object-read` APIs?

**A:** You can use the `filter` parameter to apply dynamic, SQL-like conditions. It accepts a JSON-stringified array of condition strings. The framework automatically parses these and safely converts them into the underlying database queries.

**Syntax Examples:**
- **Equality/Inequality:** `"status = 1"`, `"type neq 9"`
- **Comparisons:** `"views > 10"`, `"rating < 5"`, `"price lte 1000"`
- **Null Checks:** `"deleted_at is null"`, `"updated_by_id is distinct from null"`
- **Pattern Matching:** `"title ilike %Test%"`, `"code ~ ^CODE_"` (Regex)
- **Lists & Ranges:** `"status in 1|2|3"`, `"rating between 1|5"`
- **Array/JSON Operations:** `"tag contains tag1"`, `"metadata exists active"`

**Usage:**
```json
"filter": ["status = 1", "views > 10", "title ilike %Test%"]
```

---

### Q: How does the `relation` parameter work for fetching joined data?

**A:** The `relation` parameter allows you to perform highly efficient, declarative SQL joins to fetch related data or perform aggregations from other tables in a single API call. It accepts an array of formatted strings.

**Syntax Format:**
`"local_col, target_table, target_col, action|limit, return_fields"`

**Examples:**
- **Fetch specific fields from a related table:** 
  `"created_by_id,users,id,fetch|1,username,name,email"`
  *(Joins the `users` table where `users.id = created_by_id`, fetches 1 record, and returns only the username, name, and email).*

- **Perform aggregations on a related table:**
  `"id,action_test_report,test_id,count,*"`
  *(Counts all records in `action_test_report` where `test_id = id`).*
  You can also use `sum`, `avg`, `min`, and `max` (e.g., `"id,action_test_feedback,test_id,avg,rating"`).

---

### Q: How do I enable caching for a specific API endpoint?

**A:** You can enable caching for an API by defining the `"api_cache_sec"` key for the endpoint in the `config_api` dictionary inside `core/config.py`. It accepts a list where the first item is the cache storage mode (`"inmemory"` or `"redis"`) and the second item is the TTL (Time-To-Live) in seconds.

**Examples:**
```python
config_api = {
    # Mode: inmemory (Uses local RAM, extremely fast but doesn't share across multiple server instances)
    "/public/object-read": {"id": 14, "api_cache_sec": ["inmemory", 100]},
    
    # Mode: redis (Uses external Redis server, best for distributed caching across instances)
    "/info": {"id": 17, "api_cache_sec": ["redis", 300]}
}
```

---

### Q: How do I enable rate limiting for a specific API endpoint?

**A:** Rate limiting is configured similarly using the `"api_ratelimiting_times_sec"` key in `config_api`. It accepts a list containing the storage mode (`"inmemory"` or `"redis"`), the maximum number of allowed requests, and the time window in seconds.

**Examples:**
```python
config_api = {
    # Mode: inmemory (Tracks limits locally per server instance)
    "/public/export": {"id": 19, "api_ratelimiting_times_sec": ["inmemory", 10, 60]},
    
    # Mode: redis (Tracks limits globally across all server instances)
    "/public/heavy-task": {"id": 20, "api_ratelimiting_times_sec": ["redis", 5, 60]}
}
```

---

### Q: How do I add a new PostgreSQL table?

**A:** To create a new table and start the service normally, adding the table definition under `config_postgres["table"]` in `core/config.py` is enough. On app startup, the schema initializer reads that config and creates or syncs the table when `config_is_enable_postgres_init_startup = 1`.

**Mandatory for schema creation:**
- Add the table inside `config_postgres["table"]`.
- The first column must be exactly `{"name":"id","datatype":"bigserial","is_primary":1}`.
- Use valid PostgreSQL datatypes, keep column names unique, and avoid reserved keywords.
- If a column uses `index` or `unique`, make sure the referenced columns exist in the same table.

**Recommended when using generic object APIs:**
- Add `created_at` and `created_by_id` if the table will use `/my/object-create`, `/public/object-create`, or `/admin/object-create`.
- Add `updated_at` and `updated_by_id` if the table will use `/my/object-update` or `/admin/object-update`.
- Add `deleted_at`, `deleted_by_id`, `deactivated_at`, or similar lifecycle columns only if the table needs those states.
- Add indexes for columns commonly used in filters, ownership checks, ordering, or relation lookups.

**Optional related configs to review:**
- `config_table`: Add the table only if it needs `retention_day` cleanup or a custom `buffer_limit`.
- `config_table_create_disable_my`: Add the table if logged-in users should not create records through `/my/object-create`.
- `config_table_create_enable_public`: Add the table only if unauthenticated users may create records through `/public/object-create`.
- `config_table_read_enable_public`: Review this before adding private data. If it is set to `["*"]`, new tables are publicly readable through `/public/object-read`.
- `config_users_ownership_column`: Add a non-standard ownership column only if `/my/object-read` should support that column as an ownership filter.
- `config_column_int_mapping`: Add labels for `smallint` category columns such as `status`, `type`, or `role`.
- `config_sensitive_table`: Add sensitive tables that should be protected from accidental retention cleanup. This is not an API permission setting.
- `config_postgres["sql"]["index"]`: Add custom SQL indexes only for partial indexes or advanced indexes that the column-level `index` setting cannot express.

If none of those optional behaviors are needed, the `config_postgres["table"]` entry alone is enough for the table to be created during startup.

---

### Q: What is the use of `config_table` in `core/config.py`?

**A:** `config_table` defines table-level operational behavior that is separate from the PostgreSQL schema in `config_postgres`. Use it when a table needs background cleanup or buffered writes.

**Example:**
```python
config_table = {
    "test": {"buffer_limit": 10},
    "log_api": {"retention_day": 30, "buffer_limit": 10},
    "log_users_password": {"retention_day": 90},
    "otp": {"retention_day": 30},
}
```

**Supported keys:**
- **`retention_day`**: Automatically removes old records after the configured number of days. This is used by cleanup scripts for temporary or sensitive tables such as logs and OTPs.
- **`buffer_limit`**: Buffers high-frequency inserts in memory and flushes them in bulk when the limit is reached or during the periodic buffer flush. This is useful for write-heavy tables such as `log_api`.

If a table is not listed in `config_table`, Atom uses the default behavior for create/update/read operations and does not apply table-specific retention or buffer settings.

---

### Q: What is the use of `actor_tracking_column` in `config_postgres`?

**A:** `actor_tracking_column` maps lifecycle timestamp columns to the user ID columns that should record who performed that lifecycle action. During schema initialization, Atom creates an automatic `BEFORE UPDATE` trigger for matching tables. When a mapped timestamp changes, the trigger copies `updated_by_id` into the mapped actor column.

**Example:**
```python
"actor_tracking_column": {
    "deleted_at": "deleted_by_id",
    "deactivated_at": "deactivated_by_id",
    "archived_at": "archived_by_id",
    "verified_at": "verified_by_id"
}
```

If `deleted_at` changes and `updated_by_id = 10`, then `deleted_by_id` is automatically set to `10`.

The trigger is added only for tables that contain `updated_by_id` and both columns in the mapping, such as `deleted_at` and `deleted_by_id`. If the actor column is explicitly changed in the same update, Atom keeps that explicit value instead of overwriting it.

---
