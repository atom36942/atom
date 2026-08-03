# Query runners

Atom provides privileged query APIs for PostgreSQL, Microsoft SQL Server, and ClickHouse. The APIs shown when the API Runner is filtered by `query` are implemented in [`router/admin.py`](../router/admin.py). MongoDB query runners are not currently included.

All endpoints use `POST`, require an admin bearer token, and accept JSON. Read endpoints return JSON records, export endpoints stream CSV, and write endpoints execute non-read statements.

## Endpoint summary

| Endpoint | Database | Purpose | Roles |
|----------|----------|---------|-------|
| `/admin/postgres-query-runner-write` | PostgreSQL | Execute a non-read statement on the primary database | `1` |
| `/admin/postgres-query-runner-read` | PostgreSQL | Execute one read-only query | `1`, `2` |
| `/admin/postgres-query-runner-read-export` | PostgreSQL | Stream a read-only query as CSV | `1`, `2` |
| `/admin/postgres-query-generator-ai` | PostgreSQL | Generate validated read-only SQL from a question | `1`, `2` |
| `/admin/mssql-query-runner-write` | MSSQL | Execute and commit a non-read statement | `1` |
| `/admin/mssql-query-runner-read` | MSSQL | Execute a read query | `1`, `2` |
| `/admin/mssql-query-runner-read-export` | MSSQL | Stream a read query as CSV | `1`, `2` |
| `/admin/clickhouse-query-runner-write` | ClickHouse | Execute one non-read statement | `1` |
| `/admin/clickhouse-query-runner-read` | ClickHouse | Execute one read-only query | `1`, `2` |
| `/admin/clickhouse-query-runner-read-export` | ClickHouse | Stream a read-only query as CSV | `1`, `2` |

Role `1` is the root administrator. Role `2` can use read and export operations but cannot use write runners. Exact authorization and freshness modes are defined in `config_api` in [`config.py`](../config.py).

## Shared request and response formats

The SQL runners accept one field:

```json
{
  "sql": "SELECT 1"
}
```

A successful read response has the standard Atom envelope:

```json
{
  "status": 1,
  "message": [
    {"value": 1}
  ]
}
```

Write responses use the same envelope, with a database-specific command result in `message`. Export endpoints return a `text/csv` download instead of JSON.

Use the following headers:

```text
Authorization: Bearer <admin-access-token>
Content-Type: application/json
```

The shared limits are:

| Configuration | Default | Applies to |
|---------------|---------|------------|
| `config_query_runner_read_limit` | `5000` | JSON read responses |
| `config_query_runner_export_limit` | `50000` | CSV exports |

## Database clients

Atom creates query-runner clients during the FastAPI lifespan only when their corresponding configuration value is present. Each initialized client is exposed through `request.app.state` and closed during application shutdown.

| Database | Python driver | Configuration | Runtime client |
|----------|---------------|---------------|----------------|
| PostgreSQL | `asyncpg` | `config_postgres_url` | `app.state.client_postgres` |
| Named PostgreSQL database | `asyncpg` | `config_postgres_url_<name>` | `app.state.client_postgres_dict[name]` |
| Microsoft SQL Server | `aioodbc` | `config_mssql_url` | `app.state.client_mssql` |
| ClickHouse | `clickhouse-connect` | `config_clickhouse_url` | `app.state.client_clickhouse` |

### PostgreSQL client

The primary `asyncpg` pool uses `config_postgres_pool_min_size` and `config_postgres_pool_max_size`. Write queries always use this primary pool. Each `config_postgres_url_<name>` environment variable creates another pool that supported read, export, and AI endpoints can select using `?db=<name>`.

```env
config_postgres_url=postgresql://atom:password@postgres-host:5432/atom
config_postgres_url_analytics=postgresql://reader:password@analytics-host:5432/analytics
```

### MSSQL client

The MSSQL client is an `aioodbc` connection pool created from `config_mssql_url`. Its connections use a 60-second pool recycle interval. The pool is closed and awaited during application shutdown.

```env
config_mssql_url=Driver={ODBC Driver 18 for SQL Server};Server=tcp:mssql-host,1433;Database=atom;Uid=atom;Pwd=password;Encrypt=yes;TrustServerCertificate=no;
```

The configured ODBC driver must also be installed in the operating system running Atom.

### ClickHouse client

The ClickHouse integration uses the official asynchronous `clickhouse-connect` client. `config_clickhouse_url` is passed as its DSN, and the client is closed asynchronously during application shutdown.

```env
config_clickhouse_url=http://default:password@clickhouse-host:8123/default
```

Use port `8123` for HTTP or the server's configured HTTPS port, commonly `8443`. The native ClickHouse protocol used by `clickhouse client` on port `9000` is not supported by this driver integration.

If a required configuration value is absent, its client remains `None` and the corresponding endpoint returns a `... client not initialized` error.

## PostgreSQL

Configure the primary database with `config_postgres_url`. Named databases configured as `config_postgres_url_<name>` can be selected by the read, export, and AI endpoints using `?db=<name>`. The write endpoint always uses the primary database.

### Read

`POST /admin/postgres-query-runner-read`

The runner accepts a single `SELECT` or `WITH` statement. It executes inside a read-only transaction, applies a 30-second statement timeout, and wraps the query with the configured row limit.

```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-read" \
  -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT id, username FROM users ORDER BY id LIMIT 10"}'
```

Select a named database:

```text
POST /admin/postgres-query-runner-read?db=analytics
```

### Export

`POST /admin/postgres-query-runner-read-export`

It applies the same single-statement and read-only restrictions and streams up to `config_query_runner_export_limit` rows.

```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-read-export" \
  -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT id, username FROM users ORDER BY id"}' \
  -o postgres_query_result.csv
```

### Write

`POST /admin/postgres-query-runner-write`

Use this endpoint for statements such as `INSERT`, `UPDATE`, `DELETE`, and DDL. Read-like statements and `RETURNING` are rejected. Execution has a 15-second timeout.

```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-write" \
  -H "Authorization: Bearer <root-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql":"UPDATE test SET status = 1 WHERE id = 10"}'
```

### AI query generator

`POST /admin/postgres-query-generator-ai`

This endpoint generates SQL but does not execute it. The request selects `gemini` or `openai` and supplies a natural-language question:

```json
{
  "ai": "gemini",
  "question": "Show the latest 10 users"
}
```

The service must have `config_gemini_key` or `config_openai_key` configured. Generated SQL is restricted to `SELECT`/`WITH`, validated against the live PostgreSQL schema, limited to known objects and columns, and capped by `config_query_runner_read_limit`. Filters must use indexed columns.

Example response:

```json
{
  "status": 1,
  "message": {
    "sql": "SELECT id, username FROM users ORDER BY id DESC LIMIT 10;",
    "message": "SQL generated in the editor. Review before Run or Export.",
    "warnings": []
  }
}
```

Review generated SQL before submitting it to a runner.

## Microsoft SQL Server

Configure MSSQL with `config_mssql_url`.

### Read

`POST /admin/mssql-query-runner-read`

The query must start with `SELECT` or `WITH`. Write and execution keywords—including `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `EXEC`, `EXECUTE`, and `INTO`—are rejected. Results are fetched in batches and capped by the read limit.

```json
{
  "sql": "SELECT TOP 10 * FROM OrgHeader"
}
```

The runner retries transient `08S01` connection failures up to two times after the initial attempt.

### Export

`POST /admin/mssql-query-runner-read-export`

This endpoint applies the same read restrictions and streams CSV up to the export limit.

```bash
curl -X POST "http://localhost:8000/admin/mssql-query-runner-read-export" \
  -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT TOP 100 * FROM OrgHeader"}' \
  -o mssql_query_runner_read_export.csv
```

### Write

`POST /admin/mssql-query-runner-write`

The endpoint rejects statements starting with `SELECT` or `WITH`, executes the supplied statement, and commits the transaction.

```json
{
  "sql": "UPDATE OrgHeader SET IsActive = 1 WHERE Id = 10"
}
```

## ClickHouse

Configure ClickHouse with an HTTP or HTTPS DSN:

```env
config_clickhouse_url=http://default:<password>@clickhouse-host:8123/default
```

The official `clickhouse-connect` driver uses the HTTP interface. Native ClickHouse CLI port `9000` is not supported by this integration.

### Read

`POST /admin/clickhouse-query-runner-read`

The endpoint accepts one `SELECT` or `WITH` statement. It enables ClickHouse read-only mode, sets a 30-second execution limit, and wraps the query with `config_query_runner_read_limit`.

```bash
curl -X POST "http://localhost:8000/admin/clickhouse-query-runner-read" \
  -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT database, name, engine FROM system.tables LIMIT 10"}'
```

### Export

`POST /admin/clickhouse-query-runner-read-export`

The endpoint applies the same validation and read-only settings, requests `CSVWithNames` from ClickHouse, and streams the result without materializing the complete export in API memory.

```bash
curl -X POST "http://localhost:8000/admin/clickhouse-query-runner-read-export" \
  -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT database, name, engine FROM system.tables"}' \
  -o clickhouse_query_runner_read_export.csv
```

### Write

`POST /admin/clickhouse-query-runner-write`

The endpoint accepts one non-read statement and applies a 30-second execution limit. Statements beginning with `SELECT`, `WITH`, `EXPLAIN`, `SHOW`, `DESCRIBE`, `DESC`, or `EXISTS` are rejected and must use the read endpoint where supported.

```json
{
  "sql": "ALTER TABLE events DELETE WHERE created_at < now() - INTERVAL 90 DAY"
}
```

The API Runner intentionally does not prefill an example for this endpoint, reducing the chance of accidentally running a sample write.

## Operational safety

- Treat every query runner as privileged production access.
- Use role `1` only for writes and give role `2` read access only where necessary.
- Use database credentials with the least privileges required. A read-only database account provides protection beyond API validation.
- Never expose these endpoints publicly without Atom authentication and authorization.
- Avoid running schema changes or broad updates during peak traffic.
- Back up important data before destructive statements.
- Review AI-generated SQL before execution.
- Query text and errors may appear in Atom API logs; do not place secrets in SQL.

## Common errors

| Error | Meaning |
|-------|---------|
| `... client not initialized` | The relevant database URL/DSN is not configured or the app has not been restarted. |
| `SQL is required` | The JSON body is missing a non-empty `sql` value. |
| `Only one SQL statement is allowed` | PostgreSQL or ClickHouse input contains multiple statements. |
| `Only SELECT/WITH queries are supported` | A non-read statement was sent to a PostgreSQL or ClickHouse read endpoint. |
| `read mode restricted` | MSSQL read validation found an unsupported statement or write keyword. |
| `read SQL must use ...-read` | A read statement was sent to a write endpoint. |
| `401` or `403` response | The token is missing, invalid, or does not have an allowed role. |
