<details>
<summary>About</summary>

- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated and full flexible to extend
- Tech Stack: Python, FastAPI, Postgres, Redis, S3, Celery, RabbitMQ, Kafka, Sentry
</details>

<details>
<summary>Setup</summary>

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
</details>

<details>
<summary>Setup with Docker</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
</details>

<details>
<summary>Consumers</summary>

```bash
./venv/bin/python consumer.py celery
./venv/bin/python consumer.py rabbitmq
./venv/bin/python consumer.py redis
./venv/bin/python consumer.py kafka
```
</details>

<details>
<summary>API Controls</summary>

### Configuring `config_api`
API behaviors like authentication, caching, and rate limiting are controlled per-route in the `config_api` dictionary.

| Setting Name | Modes Available | TTL / Parameter Source | Execution Logic |
| :--- | :--- | :--- | :--- |
| `user_is_active_check` | `redis`, `realtime`, `inmemory`, `token` | `config_redis_cache_ttl_sec` | Verifies `is_active=1` |
| `user_role_check` | `redis`, `realtime`, `inmemory`, `token` | `config_redis_cache_ttl_sec` | Matches IDs in list (e.g. `[1, 2]`) |
| `api_cache_sec` | `redis`, `inmemory` | Inbuilt (e.g. `["redis", 60]`) | Full Response Gzip/Base64 |
| `api_ratelimiting_times_sec` | `redis`, `inmemory` | Inbuilt (e.g. `["inmemory", 3, 10]`) | Sliding Window Counter |

### Mode Definitions
- **`redis`**: Distributed state via Redis keys.
- **`inmemory`**: Local state via `app.state` dictionaries.
- **`realtime`**: Live PostgreSQL queries for zero stale data.

</details>

<details>
<summary>Authentication</summary>

### Route Protection
The framework enforces authentication automatically based on a unified path prefix system.

| Prefix Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Open for login, signup, and OTP flows. |
| `/public/` | Public | Data endpoints for general access. |
| `/` | Public | General root endpoints. |
| `/my/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/private/` | **Protected** | Strictly requires a valid `Bearer` token. |
| `/admin/` | **Role-Based** | Requires token **AND** matching role in `config_api`. |

### Manual Enforcement
For any public route where you want to selectively verify a user, check the `request.state.user` dictionary:

```python
# Force auth in a public route
if not request.state.user:
    raise Exception("unauthorized access")
```

### Context Injection
The `request.state.user` object is populated by the middleware using `func_authenticate`. It contains decoded JWT data (id, type, role, is_active) for use across any API function.

</details>

<details>
<summary>API Roles</summary>

### Direct API Role Passing
To maximize clarity and minimize side effects, the framework avoids storing the `api_role` in a global request state. Instead, roles are passed as literal strings directly to the backend functions that require them (e.g., table creation or update logic).

### Implementation Pattern
Role-aware logic is only implemented where necessary. The role is passed as a string parameter within the `router.py` endpoint:

```python
@router.post("/my/object-create")
async def func_api_my_object_create(request:Request):
   ...
   return {"status":1,"message":await func_obj_create_logic("my", ...)}
```

### Core API Roles
| Role | Category | Application Area |
| :--- | :--- | :--- |
| **`auth`** | Identity | Authentication, signup, and login flows. |
| **`my`** | Private | User-specific data and account management. |
| **`public`** | General | Unprotected data and utility converters. |
| **`private`** | Internal | Protected utility endpoints (e.g., S3). |
| **`admin`** | System | Administrative maintenance and database init. |
| **`index`** | Root | Root path, OpenAPI spec, and dynamic pages. |

### How to Extend Roles
To add a new API role to the system:

1. **Update Config**: Add the new role name to the `config_api_roles` list in `config.py`.
2. **Assign in Router**: When calling role-aware functions in `router.py`, pass your new role string directly as a parameter.
3. **Validation**: The system will automatically validate all registered routes against the `config_api_roles` whitelist during the startup lifespan.

</details>


<details>
<summary>API Parameters</summary>

### Standard Parameter Reading
All API parameters (headers, query, form, or JSON body) are extracted and validated using the `func_request_param_read` pure function. This ensures strict type safety and mandatory field enforcement before core logic executes.

### Usage Pattern
```python
obj_body = await func_request_param_read(request, "body", [
    ("email", "str", 1, None, None),
    ("age", "int", 0, None, 18),
    ("tags", "list:str", 0, ["tech", "news"], None)
])
```

### Config Structure
Each parameter is defined by a tuple: `(name, type, is_mandatory, allowed_values, default_value)`

### Allowed Datatypes
| Type | Logic / Alias | Behavior |
| :--- | :--- | :--- |
| **`str`** | `str` | Standard string casting. |
| **`int`** | `integer`, `int4`, `int8`, `bigint`, `smallint` | Casts input to integer. |
| **`float`** | `number`, `numeric` | Casts input to floating point number. |
| **`bool`** | `bool` | **Smart Boolean**: Returns `1` for `true`, `yes`, `on`, `ok`, or `1`. |
| **`list`** | `list` | **Smart List**: Handles JSON arrays or splits comma-separated strings. |
| **`list:<type>`**| `list:int`, `list:str`, etc. | Recursive casting for every element in a list. |
| **`dict`** | `object` | Expects and returns a JSON dictionary/object. |
| **`file`** | `file` | Handles multipart uploads; returns a `list` of file objects. |
| **`any`** | `any` | Passes the raw value through without any type casting. |

</details>


<details>
<summary>Database Init</summary>

### System Initialization
The database structure is managed through administrative endpoints and automated startup checks.

| Feature | Endpoint / Function | Behavior |
| :--- | :--- | :--- |
| **Schema Init** | `/admin/postgres-init` | Triggers `func_postgres_init` to create extensions and base tables. |
| **Root User** | `func_postgres_init_root_user` | Automatically creates the first admin user during `main.py` lifespan. |
| **Auto-Table** | `func_postgres_create` | Creates tables on-the-fly if missing during buffer flushes. |

### PostgreSQL Controls
Operational constraints for database management are defined in `config_postgres["control"]`.

| Control Name | Default | Execution Logic |
| :--- | :--- | :--- |
| `is_extension` | 1 | Enables PostgreSQL extension creation (e.g., `pg_trgm`, `postgis`). |
| `is_match_column` | 0 | Forces strict column matching between config and database. |
| `is_drop_disable_table` | 1 | Prevents accidental `DROP TABLE` operations via automated tasks. |
| `is_truncate_disable` | 1 | Prevents accidental `TRUNCATE` operations via automated tasks. |
| `is_child_delete_soft` | 1 | Enables soft deletion for child records when a parent is deleted. |
| `is_child_delete_hard` | 1 | Enables hard deletion for child records when a parent is deleted. |
| `is_delete_disable_role` | 1 | Restricts delete operations based on user roles defined in config. |
| `delete_disable_bulk` | `[["users", 1]]` | Prevents bulk deletion for specific tables and row types. |
| `delete_disable_table` | `["users"]` | Entirely disables the delete API for the specified tables. |

### Column Properties
Each field in a `config_postgres["table"]` entry is a map defining column behavior.

| Property | Default | Execution Logic |
| :--- | :--- | :--- |
| `name` | - | Primary database column identifier. |
| `datatype` | - | Target PostgreSQL data type (e.g. `timestamptz`, `bigint[]`). |
| `default` | - | SQL default value (e.g. `now()`, `0`). |
| `index` | - | Index types to create (e.g. `btree`, `gin`, `gist`). |
| `unique` | - | Composite or single unique groups (comma/pipe separated). |
| `in` | - | Check constraint values (e.g. `(0, 1)`). |
| `is_mandatory` | 0 | Enforces non-null checks in API and UI. |
| `regex` | - | Pattern validation for browser and API inputs. |
| `old` | - | Migration helper to rename columns during schema init. |

</details>

<details>
<summary>Postgres Create</summary>

### `func_postgres_create`
High-performance record insertion with support for in-memory buffering and batching.

| Parameter | Type | Default | Execution Logic |
| :--- | :--- | :--- | :--- |
| `object_list` | `list` | - | List of dictionaries to insert. |
| `execution_mode` | `str` | `now` | `now`: immediate insert, `buffer`: in-memory batching, `flush`: clear buffer. |
| `is_serialize` | `int` | `0` | If `1`, runs `func_postgres_obj_serialize` before insertion. |
| `table_buffer` | `int` | `0` (500) | Threshold count for the in-memory buffer before flushing. |

#### Features
- **Buffer Mode**: Reduces database I/O for high-frequency logs.
- **Protocol Safety**: Uses `jsonb_to_recordset` for bulk inserts with a single bind parameter.

</details>

<details>
<summary>Postgres Update</summary>

### `func_postgres_update`
Batch updating with owner validation and parameter overflow protection.

| Parameter | Type | Default | Execution Logic |
| :--- | :--- | :--- | :--- |
| `obj_list` | `list` | - | List containing `id` and columns to update. |
| `created_by_id` | `int` | `None` | If provided, enforces `WHERE created_by_id = X` ownership. |
| `batch_size` | `int` | `5000` | Target rows per query (dynamically capped for safety). |
| `is_return_ids` | `int` | `0` | If `1`, returns list of modified record IDs. |

#### Features
- **Protocol Safety**: Automatically calculates batch size to never exceed the **65,535** parameter limit.
- **Ownership Check**: Built-in verification to prevent cross-user updates.

</details>

<details>
<summary>Postgres Read</summary>

### `func_postgres_read`
Generic object reader with advanced filtering, sorting, and pagination.

| Setting | Usage | Execution Logic |
| :--- | :--- | :--- |
| **Filters** | `field,op,val` | `contains`, `exists`, `overlap`, `any`, `in`, `between`, `point`. |
| **Sorting** | `order=id desc` | Comma-separated list for complex ordering. |
| **Columns** | `column=id,name` | Select specific fields to reduce payload. |
| **Relations** | `creator_key=name` | Automatically fetches creator details from `users`. |
| **Aggregates** | `action_key=...` | Cross-table count/sum relations without extra queries. |

#### Filter Examples
- **Spatial**: `location,point,lon|lat|min|max`
- **JSONB**: `data,contains,key|value|type`
- **Arrays**: `tags,overlap,tagA|tagB`

</details>

<details>
<summary>Request Parameter Config</summary>

### API Parameter Validation
The `func_request_param_read` function uses a `param_config` list to extract and validate inputs. Each entry in the list is a tuple or list with the following structure:

| Position | Property | Default | Execution Logic |
| :--- | :--- | :--- | :--- |
| **Index 0** | `name` | - | The key name in the request (query, body, form, header). |
| **Index 1** | `datatype` | - | Target type: `int`, `str`, `float`, `bool`, `list`, `file`, or `any`. |
| **Index 2** | `is_mandatory` | 0 | If 1, raises an error if the parameter is missing or empty. |
| **Index 3** | `enum` | None | List of allowed values (e.g. `["soft", "hard"]`). |
| **Index 4** | `default` | None | Default value if the parameter is missing and not mandatory. |

### Example Usage
```python
obj_query = await func_request_param_read(
    request, 
    "query", 
    [("mode", "str", 1, ["soft", "hard"], "soft")]
)
```

</details>

<details>
<summary>Admin Sync</summary>

### Operational Maintenance
The `/admin/sync` endpoint is used to align the application state with the database and configuration.

- **Buffer Flush**: Forces all pending `buffer` mode database operations to commit.
- **Schema Refresh**: Re-scans PostgreSQL to update `cache_postgres_schema` and table/column lists.
- **Map Updates**: Reloads `cache_users_role` and `cache_users_is_active` for real-time auth performance.
- **Route Validation**: Runs `func_check` to ensure `config_api` matches actual application routes.
- **Data Cleanup**: Executes `func_postgres_clean` to prune old logs based on `retention_day` settings.

</details>

<details>
<summary>Import Tools</summary>

### Bulk Data Management
The framework provides high-performance administrative tools to import or remove data in bulk. All import APIs process files in memory-efficient chunks (5,000 rows).

| Data Store | Operation | Endpoint | Parameters |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | Consolidated | `/admin/postgres-import` | `mode`, `table`, `file` |
| **Redis** | **Create** | `/admin/redis-import-create` | `table`, `file`, `expiry_sec` |
| | **Delete** | `/admin/redis-import-delete` | `table`, `file` |
| **MongoDB** | Consolidated | `/admin/mongodb-import` | `mode`, `database`, `table`, `file` |

### Mode Implementation Pattern
We follow the **Selective Consolidation** pattern to ensure API cleanliness:
- **Consolidated**: When all modes (`create`, `update`, `delete`) share the exact same parameter set (e.g., Postgres, MongoDB).
- **Split**: When action-specific parameters exist (e.g., Redis `create` requires `expiry_sec` while `delete` does not).

### CSV Structure Requirements
For all delete and update operations, a column named **`id`** is mandatory in the CSV file.

#### 1. PostgreSQL (Consolidated)
- **Mode: `create`**: CSV columns must match the database table schema.
- **Mode: `update`**: Requires `id` column + columns you wish to update.
- **Mode: `delete`**: Only requires the `id` column.

#### 2. Redis (Split)
- **Key Pattern**: Entries are stored as `{table}_{id}`.
- **API: `redis-import-create`**: Requires `id` column. The entire row is stored as a JSON string.
- **API: `redis-import-delete`**: Requires `id` column to identify keys for removal.

#### 3. MongoDB (Consolidated)
- **Mode: `create`**: CSV columns are converted to document fields.
- **Mode: `delete`**: Requires an `id` or `_id` column. Standard 24-char hex strings are automatically converted to `ObjectId`.

### Cloud Operations (S3)
We follow the **Selective Consolidation** pattern for AWS S3 management:
- **Consolidated: `s3-bucket-ops`**: Handles all bucket-level actions (`bucket_create`, `bucket_public`, `bucket_empty`, `bucket_delete`) as they share the same `bucket` query parameter.
- **Split: `s3-url-delete`**: Dedicated endpoint for batch URL removal, requiring a different parameter structure (`url` list in the request body).

</details>

<details>
<summary>Static Assets</summary>

### Serving Files
The framework mounts a static directory to serve frontend assets and documentation.

- **Storage**: Files located in the `./static` directory.
- **Access**: Available at the `/static/` URL prefix (e.g., `http://localhost:8000/static/api.html`).
- **Configuration**: Managed in `main.py` via `func_app_add_static(app, "./static", "/static")`.

</details>

<details>
<summary>Page Rendering</summary>

### Dynamic HTML Serving
The `/page-{name}` route provides a simple way to serve HTML content from the static folder.

- **Pattern**: `GET /page-dashboard` -> Searches for `static/dashboard.html`.
- **Location**: Place your custom `.html` files anywhere inside the `static/` directory or its subdirectories.
- **Search Logic**: Uses `func_html_serve` to recursively search the `static/` folder if the file isn't at the root.
- **Security**: Prevents directory traversal using `..` checks and path resolution.
- **Response**: Returns a standard `HTMLResponse` with UTF-8 encoding.

</details>

<details>
<summary>Global Switches</summary>

### Application State Controls
Generic application-wide behaviors are controlled by boolean switches starting with `config_is_`.

| Switch Name | Default | Behavior |
| :--- | :--- | :--- |
| `config_is_signup` | 1 | Enables/disables the public signup endpoint. |
| `config_is_log_api` | 1 | Toggles automatic non-GET request logging to `log_api`. |
| `config_is_traceback` | 1 | Shows full python errors in the API response. |
| `config_is_prometheus` | 0 | Enables/disables the `/metrics` endpoint. |
| `config_is_reset_tmp` | 1 | Wipes the `./tmp` folder on every application boot. |
| `config_is_debug_fastapi` | 1 | Toggles the internal FastAPI debug flag. |
| `config_is_index_html` | 0 | Determines if root `/` serves `static/index.html`. |
| `config_is_otp_users_update_admin` | 0 | Strict verification for admin-led user data updates. |

</details>

<details>
<summary>Adding Routers</summary>

### Extensible API Architecture
The framework automatically discovers and mounts new FastAPI routers without manually modifying `main.py`. This is powered by `func_add_router(app)`.

- **Root Directory**: Create a file with a name starting with `router` (e.g., `router_billing.py`).
- **Sub-directory**: Create a folder named `router` and place any `.py` file inside (e.g., `router/billing.py`).
- **Declaration**: Inside the file, export a standard `APIRouter()` as a variable named `router`.

```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/my-custom-endpoint")
async def func_api_custom():
    return {"status": 1, "message": "hello"}
```

</details>
