# API Logs

Atom records one `log_api` row after every API request. Logging is buffered so the request does not wait for an immediate database insert.

## Default behavior

By default:

```python
config_log_db = None
```

`None` means API logs use the primary PostgreSQL pool:

```python
app.state.client_postgres_log = app.state.client_postgres
```

This preserves the original behavior and requires no additional configuration.

## Store logs in another PostgreSQL database

Configure a named PostgreSQL connection and set `config_log_db` to the same name:

```bash
config_postgres_url=postgresql://atom:password@primary-db:5432/atom
config_postgres_url_logs=postgresql://logger:password@logs-db:5432/atom_logs
config_log_db=logs
```

The suffix in `config_postgres_url_logs` becomes the `client_postgres_dict` key:

```python
app.state.client_postgres_dict["logs"]
```

Lifespan resolves:

```python
app.state.client_postgres_log = app.state.client_postgres_dict["logs"]
```

The mapping is exact and case-sensitive. For example, `config_log_db=logs` selects `config_postgres_url_logs`. If `config_log_db` names a pool that does not exist, startup fails with a configuration error instead of silently writing logs to primary.

## Dedicated log buffer

The new log database uses an in-memory buffer, but you do not need to configure or create it manually. Atom automatically creates:

```python
app.state.cache_postgres_buffer_log_api
```

Normal buffered records continue using:

```python
app.state.cache_postgres_buffer_create
```

This separation prevents application rows and API logs from being flushed to the wrong database:

```text
Normal buffered rows
    → cache_postgres_buffer_create
    → client_postgres

API logs
    → cache_postgres_buffer_log_api
    → client_postgres_log
    → client_postgres_dict[config_log_db] when configured
    → log_api
```

The periodic lifespan task calls `func_postgres_buffer_flush` for both buffers every 60 seconds. It calls the same helper for a final flush during graceful shutdown. Primary and log flush errors are isolated, so a primary failure does not prevent an independent logging database from flushing.

The `log_api` table-specific `buffer_limit` in `config_table` still controls early log-buffer release:

```python
config_table = {
    "log_api": {"retention_day": 30, "buffer_limit": 10},
}
```

## Database schema

Schema initialization runs against primary only. When `config_log_db` selects an independent database, that database must already contain a compatible `log_api` table.

Log serialization and validation currently use the primary `cache_postgres_schema`. The selected logging database does not need a separate schema cache as long as its `log_api` table has the same structure as primary. A separate schema cache would only be necessary if the external log table structure differs.

The required schema is declared under:

```python
config_postgres["table"]["log_api"]
```

Apply the corresponding table definition through your migration or deployment process before routing logs to the external database. You only need to ensure:

- The external database contains a compatible `log_api` table.
- Its database user has `INSERT` permission.
- The configured names match, such as `config_postgres_url_logs` with `config_log_db=logs`.

## Failure behavior

API logging is wrapped with exception suppression. A logging failure does not fail the API response. This keeps observability infrastructure from taking down application traffic, but it also means operators should monitor the logging database and application error output.

If the selected logging database becomes unavailable:

- New log inserts or buffer releases can fail.
- The API response continues normally.
- Buffered logs remain process-local and are not a durable queue.
- Process termination before a successful flush can lose buffered log entries.

Use database monitoring and graceful deployment shutdowns when API logs are operationally important.

## Connection sizing

The logging database uses a pool already created through `client_postgres_dict`; it does not create an additional pool for the same name. The pool uses:

```python
config_postgres_pool_min_size
config_postgres_pool_max_size
```

Include the named logging pool when calculating total PostgreSQL connections across application instances. See [postgres.md](postgres.md#pool-sizing).

## Examples

Keep logs on primary:

```bash
config_postgres_url=postgresql://atom:password@primary-db:5432/atom
# config_log_db is unset
```

Send logs to the `logs` database:

```bash
config_postgres_url=postgresql://atom:password@primary-db:5432/atom
config_postgres_url_logs=postgresql://logger:password@logs-db:5432/atom_logs
config_log_db=logs
```

Use the same named database for analytics reads:

```bash
curl -X POST "http://localhost:8000/admin/postgres-query-runner-read?db=logs" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT path, count(*) FROM log_api GROUP BY path ORDER BY count(*) DESC"}'
```

Only expose a named database through selectable read APIs when its schema and access policy are appropriate.

---

📚 [PostgreSQL guide](postgres.md) · [Back to README](../readme.md)
