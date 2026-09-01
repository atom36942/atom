# PostgreSQL

Atom supports one primary PostgreSQL pool and any number of named pools. Built-in APIs use named pools for selectable read traffic, but custom APIs can also use them to connect to independent or third-party PostgreSQL databases.

## Primary pool

Set the primary connection URL in `.env`:

```bash
config_postgres_url=postgresql://atom:password@primary-db:5432/atom?sslmode=require
```

At startup, this creates:

```python
app.state.client_postgres
```

`client_postgres` is the authoritative primary pool. Atom uses it for:

- Every create, update, delete, import, schema-init, and buffered write.
- Authentication, OTP, authorization, and consistency-sensitive operations.
- Reads when the request does not select a named database.

Application code normally receives the pool explicitly:

```python
user = await app_state.func_user_read_single(
    client_postgres=app_state.client_postgres,
    user_id=user_id,
)
```

## Read Replicas and Named Pools

To offload heavy read traffic from the primary PostgreSQL instance, Atom supports configuring read replicas and additional named pools using environment variables.

### Read Replica Configuration

To direct read queries to a PostgreSQL read replica, set `config_postgres_url_read` (or any `config_postgres_url_<name>`) in `.env`:

```bash
config_postgres_url_read=postgresql://atom:password@read-replica-db:5432/atom?sslmode=require
```

At startup, Atom detects the `config_postgres_url_` prefix and populates `app.state.client_postgres_dict["read"]` with an `asyncpg` connection pool. Read-supported endpoints can then target this replica by specifying `?db=read`:

```bash
curl "http://localhost:8000/public/object-read?db=read&table=users"
```

### Multiple Named Pools

Add additional named PostgreSQL connection URLs using the pattern:

```text
config_postgres_url_<name>
```

For example:

```bash
config_postgres_url_read=postgresql://atom:password@read-db:5432/atom?sslmode=require
config_postgres_url_read_india=postgresql://atom:password@read-india-db:5432/atom?sslmode=require
config_postgres_url_analytics=postgresql://atom:password@analytics-db:5432/atom?sslmode=require
```

`func_config_override_from_env` removes the prefix and builds the runtime mapping:

```python
config_postgres_url_dict = {
    "read": "postgresql://...",
    "read_india": "postgresql://...",
    "analytics": "postgresql://...",
}
```

The default value of `config_postgres_url_dict` is `None`. It becomes a dictionary when matching environment variables are present.

Lifespan creates one asyncpg pool for every non-empty URL:

```python
app.state.client_postgres_dict["read"]
app.state.client_postgres_dict["read_india"]
app.state.client_postgres_dict["analytics"]
```

Routers inspect `client_postgres_dict` when the `db` parameter is provided.

## Independent and third-party databases

Despite the name `config_postgres_url_dict`, entries do not have to be read replicas. Each value is an independent asyncpg pool and can point to:

- A read replica of primary.
- A reporting or analytics database.
- A tenant-specific PostgreSQL database.
- A legacy application database.
- A PostgreSQL database operated by a third party.

For example:

```bash
config_postgres_url_read=postgresql://atom:password@read-db:5432/atom
config_postgres_url_crm=postgresql://integration:password@crm-db.example.com:5432/crm
config_postgres_url_billing=postgresql://integration:password@billing-db.example.com:5432/billing
```

These create:

```python
app.state.client_postgres_dict["read"]
app.state.client_postgres_dict["crm"]
app.state.client_postgres_dict["billing"]
```

The built-in APIs listed below treat named pools as read targets. A custom API may perform CRUD against a specific named pool when that behavior is intentional.

For a fixed integration, select the pool in server code instead of accepting a caller-controlled `db`:

```python
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/private/crm-customer")
async def func_api_private_crm_customer(*, request: Request):
    app_state = request.app.state
    client_postgres = app_state.client_postgres_dict.get("crm")
    if not client_postgres:
        raise Exception("crm postgres client not initialized")

    oq = await app_state.func_request_param_read(
        request=request,
        mode="query",
        strict=False,
        param_specs=[
            {
                "name": "customer_id",
                "type": "int",
                "required": True,
                "allowed": None,
                "default": None,
            }
        ],
    )
    record = await client_postgres.fetchrow(
        "SELECT id, name, email FROM customer WHERE id=$1",
        oq["customer_id"],
    )
    return {"status": 1, "message": dict(record) if record else None}
```

A custom write endpoint can use the same named pool:

```python
@router.put("/private/crm-customer")
async def func_api_private_crm_customer_update(*, request: Request):
    app_state = request.app.state
    client_postgres = app_state.client_postgres_dict.get("crm")
    if not client_postgres:
        raise Exception("crm postgres client not initialized")

    ob = await app_state.func_request_param_read(
        request=request,
        mode="body",
        strict=True,
        param_specs=[
            {"name": "id", "type": "int", "required": True, "allowed": None, "default": None},
            {"name": "name", "type": "str", "required": True, "allowed": None, "default": None},
        ],
    )
    result = await client_postgres.execute(
        "UPDATE customer SET name=$1 WHERE id=$2",
        ob["name"],
        ob["id"],
    )
    return {"status": 1, "message": result}
```

Register custom routes in `config_api` with the required token, role, and rate-limit policies. Use parameter-bound SQL, grant the integration database user only the permissions it needs, require TLS where supported, and keep its connection URL in the environment.

Primary-derived caches such as `cache_postgres_schema` do not describe an unrelated database. For third-party CRUD, use explicit SQL as above, or build and maintain a separate schema cache for that named database. Do not pass a third-party pool into generic schema-driven helpers unless its schema is compatible with primary.

## Selecting a database

Supported read APIs accept an optional string query parameter:

```text
db=<name>
```

Selection follows this rule:

```python
client_postgres, cache_postgres_schema, cache_postgres_schema_ai = (
    app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
)
```

Therefore:

- No `db` parameter uses primary and preserves the original behavior.
- `?db=read` uses `client_postgres_dict["read"]`.
- An unknown name fails validation and returns a clear error (`database pool '<db>' not found`).
- The caller can select only configured names, never provide a raw connection URL.

Example:

```bash
curl "http://localhost:8000/my/profile?db=read" \
  -H "Authorization: Bearer <access-token>"
```

```bash
curl "http://localhost:8000/public/object-read?db=read_india&table=test&limit=20"
```

For POST-based read tools and form imports, `db` remains a query/form parameter:

```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-read?db=analytics" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT type, count(*) FROM test GROUP BY type"}'
```

## APIs supporting `db`

| API | Purpose | Execution Model |
|-----|---------|-----------------|
| `GET /my/profile` | User profile and configured profile metadata | Pure Read |
| `GET /my/api-usage` | Current user's API usage | Pure Read |
| `GET /my/message-inbox` | Message conversation summaries | Pure Read |
| `GET /my/message-thread` | Message conversation thread | Hybrid (Read from `db`, update `read_at` on Primary) |
| `GET /my/object-read` | User scoped object read | Hybrid (Read from `db`, mark read on Primary) |
| `GET /admin/postgres-info` | Database information and statistics | Pure Read |
| `GET /admin/postgres-schema` | Live database schema | Pure Read |
| `GET /admin/object-read` | Unrestricted administrative object read | Pure Read |
| `POST /admin/postgres-query-runner-read` | Read-only SQL runner | Pure Read |
| `POST /admin/postgres-query-runner-read-export` | Read-only SQL CSV export | Pure Read |
| `POST /admin/postgres-query-generator-ai` | AI-generated read query | Pure Read |
| `POST /admin/postgres-import` | Bulk CSV/JSON import tool | Target DB Import |
| `GET /public/object-read` | Public allow-listed object read | Pure Read |
| `GET /public/table-column-values` | Public distinct column values, with counts by default | Pure Read |
| `GET /admin/table-column-values` | Admin distinct column values, with counts by default | Pure Read |

Write mutations (e.g. `/my/object-create`, `/admin/object-update`) target primary `client_postgres`. Hybrid APIs like `/my/object-read` and `/my/message-thread` fetch data from the selected `db` pool while executing state updates (like `read_at`) on primary. Authentication, token refresh, middleware security checks, and OTP verification remain on primary to avoid replica-lag inconsistencies.

## Pool sizing

Every primary or named pool uses:

```python
config_postgres_pool_min_size = 5
config_postgres_pool_max_size = 20
```

Override these values through the environment when necessary:

```bash
config_postgres_pool_min_size=1
config_postgres_pool_max_size=10
```

Estimate the maximum application connection demand with:

```text
app instances × (1 primary pool + named pool count) × max pool size
```

For example, four app instances with one primary, two replicas, and a maximum pool size of ten can request up to 120 connections. PostgreSQL connection limits must also leave capacity for migrations, administration, workers, and other services.

A minimum size of `1` is often more suitable when many named pools are configured or some pools receive infrequent traffic.

## Consistency and schema requirements

Read replicas can lag behind primary. A request routed to a replica may not immediately observe a preceding write. Keep read-after-write flows and security-sensitive reads on primary.

The schema caches (`cache_postgres_schema` and `cache_postgres_schema_ai`) are built from primary. Generic object reads, relations, filters, group-by, and AI query generation therefore assume that every selectable database has a compatible schema.

The current V1 design provides explicit named-pool selection. It does not provide:

- Automatic load balancing among replicas.
- Health-aware pool removal.
- Replica-lag monitoring.
- Automatic retry or fallback to primary.

Those features can be added later behind a centralized client selector without changing the environment-variable naming convention.

## Shutdown

During application shutdown Atom performs final flushes for the primary application buffer and the dedicated API-log buffer, then closes `client_postgres` and every pool in `client_postgres_dict`. Application writes use primary; `config_postgres_db_log_api` may route `log_api` writes to a named pool, and custom APIs may use named pools for writes when explicitly implemented. See [logs.md](logs.md).

---

📚 [Back to README](../readme.md)
