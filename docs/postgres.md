# PostgreSQL

Atom supports one primary PostgreSQL pool and any number of named pools for read-only traffic.

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

## Named read pools

Add named PostgreSQL URLs with the pattern:

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

It also exposes the initialized names as:

```python
app.state.cache_postgres_db_name_list
```

Routers use that list as the `allowed` value for `func_request_param_read`, so an unknown `db` name is rejected before lookup.

## Selecting a database

Supported read APIs accept an optional string query parameter:

```text
db=<name>
```

Selection follows this rule:

```python
client_postgres = (
    app_state.client_postgres
    if oq["db"] is None
    else app_state.client_postgres_dict[oq["db"]]
)
```

Therefore:

- No `db` parameter uses primary and preserves the original behavior.
- `?db=read` uses `client_postgres_dict["read"]`.
- An unknown name fails validation and returns the standard error response.
- The caller can select only configured names, never provide a connection URL.

Example:

```bash
curl "http://localhost:8000/my/profile?db=read" \
  -H "Authorization: Bearer <access-token>"
```

```bash
curl "http://localhost:8000/public/object-read?db=read_india&table=test&limit=20"
```

For POST-based read tools, `db` remains a query parameter:

```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-read?db=analytics" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT type, count(*) FROM test GROUP BY type"}'
```

## APIs supporting `db`

| API | Purpose |
|-----|---------|
| `GET /my/profile` | User profile and configured profile metadata |
| `GET /my/api-usage` | Current user's API usage |
| `GET /my/message-inbox` | Message conversation summaries |
| `GET /admin/postgres-info` | Database information and statistics |
| `GET /admin/postgres-schema` | Live database schema |
| `GET /admin/object-read` | Unrestricted administrative object read |
| `POST /admin/postgres-query-runner-read` | Read-only SQL runner |
| `POST /admin/postgres-query-runner-read-export` | Read-only SQL CSV export |
| `POST /admin/postgres-query-generator-ai` | AI-generated read query |
| `GET /public/object-read` | Public allow-listed object read |
| `GET /public/table-groupby` | Public grouped aggregation |

Write APIs never accept `db`; they always use `client_postgres`.

`/my/object-read` and `/my/message-thread` are not replica-selectable because they can update `read_at`. Authentication, token refresh, middleware security checks, and OTP verification also remain on primary to avoid replica-lag inconsistencies.

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

During application shutdown Atom first performs its final primary buffer flush, then closes `client_postgres` and every pool in `client_postgres_dict`. Named pools are read-only routing targets and are never used for buffered writes.

---

📚 [Back to README](../readme.md)
