# PostgreSQL Buffers

Atom can hold PostgreSQL create records briefly in application memory and insert them in batches. Buffering reduces the number of immediate database writes for high-volume, low-urgency records.

## The two buffers

Lifespan automatically creates two independent dictionaries:

```python
cache_postgres_buffer_create = {}
cache_postgres_buffer_log_api = {}
```

They are registered as:

```python
app.state.cache_postgres_buffer_create
app.state.cache_postgres_buffer_log_api
```

You do not create or configure these dictionaries manually.

The names begin with `cache_` so lifespan automatically registers them on `app.state`. They hold pending writes; they are not API-response or database-read caches.

| Buffer | Contents | Destination |
|--------|----------|-------------|
| `cache_postgres_buffer_create` | Records submitted through object-create APIs with `mode=buffer` | Primary `client_postgres` |
| `cache_postgres_buffer_log_api` | Middleware-generated `log_api` records | `client_postgres_log_api` |

`client_postgres_log_api` points to primary when `config_postgres_db_log_api=None`, or to `client_postgres_dict[config_postgres_db_log_api]` when a named logging database is configured.

## Create modes

`func_postgres_create` supports three internal modes:

| Mode | Behavior |
|------|----------|
| `now` | Validate, serialize, and insert records immediately. |
| `buffer` | Validate and serialize records, then append them to an in-memory buffer. |
| `flush` | Insert every pending group from the supplied buffer and clear successful groups. |

API callers can select `now` or `buffer`. The `flush` mode is internal and is invoked through `func_postgres_buffer_flush_all`.

## Buffer a create request

The `/my/object-create`, `/public/object-create`, and `/admin/object-create` APIs accept the optional `mode` query parameter. Its default is `now`.

Example using the authenticated user API:

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test&mode=buffer" \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "buffered example", "type": 1}'
```

The route passes the primary buffer into `func_postgres_create`:

```python
await app_state.func_postgres_create(
    client_postgres=app_state.client_postgres,
    client_postgres_conn=None,
    client_password_hasher=app_state.client_password_hasher,
    func_postgres_serialize=app_state.func_postgres_serialize,
    func_regex_check=app_state.func_regex_check,
    cache_postgres_schema=app_state.cache_postgres_schema,
    cache_postgres_buffer=app_state.cache_postgres_buffer_create,
    config_regex=app_state.config_regex,
    buffer_limit=app_state.config_table.get(
        table,
        {},
    ).get(
        "buffer_limit",
        app_state.config_buffer_limit_default,
    ),
    mode="buffer",
    table=table,
    obj_list=obj_list,
)
```

A successful buffered request returns:

```json
{"status": 1, "message": "buffered"}
```

If the request reaches the buffer limit and causes an immediate batch insert, the message is:

```json
{"status": 1, "message": "buffered released"}
```

## Use buffering in a custom API

Custom APIs do not create a new buffer. Pass the application-managed general buffer:

```python
@router.post("/my/event-create")
async def func_api_my_event_create(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(
        request=request,
        mode="body",
        strict=0,
        param_specs=[],
    )

    result = await app_state.func_postgres_create(
        client_postgres=app_state.client_postgres,
        client_postgres_conn=None,
        client_password_hasher=app_state.client_password_hasher,
        func_postgres_serialize=app_state.func_postgres_serialize,
        func_regex_check=app_state.func_regex_check,
        cache_postgres_schema=app_state.cache_postgres_schema,
        cache_postgres_buffer=app_state.cache_postgres_buffer_create,
        config_regex=app_state.config_regex,
        buffer_limit=app_state.config_table.get(
            "event",
            {},
        ).get(
            "buffer_limit",
            app_state.config_buffer_limit_default,
        ),
        mode="buffer",
        table="event",
        obj_list=[ob],
    )
    return {"status": 1, "message": result}
```

Use `mode="now"` instead when the caller must receive an inserted ID or immediately read the new record.

## How records are grouped

Buffered records are grouped by table and sorted column names:

```python
key = f"{table}|{','.join(sorted(serialized_list[0].keys()))}"
```

Example keys:

```text
test|created_by_id,title,type
test|created_by_id,description,title
log_api|created_by_id,error,ip_address,method,path,query_param,response_time_ms,response_type,status_code
```

Records with different column sets remain in separate groups so each batch insert has a consistent column layout.

Before entering the buffer, records:

- Pass `func_regex_check`.
- Pass `func_postgres_serialize`.
- Have caller-supplied `id` removed.
- Are grouped in batches of at most 5,000 during serialization.

## Buffer limits

The table-specific limit comes from `config_table`:

```python
config_table = {
    "test": {"buffer_limit": 10},
    "log_api": {"retention_day": 30, "buffer_limit": 10},
}
```

Tables without a specific value use:

```python
config_buffer_limit_default = 100
```

When a group reaches its limit, `func_postgres_create(mode="buffer")` immediately inserts that group through the client supplied by the caller and then clears the successfully inserted list.

## Automated API-log buffering

API logging is automatic. After every request, middleware creates a `log_api` object and calls:

```python
await app_state.func_postgres_create(
    client_postgres=app_state.client_postgres_log_api,
    ...
    cache_postgres_buffer=app_state.cache_postgres_buffer_log_api,
    buffer_limit=app_state.config_table.get(
        "log_api",
        {},
    ).get(
        "buffer_limit",
        app_state.config_buffer_limit_default,
    ),
    mode="buffer",
    table="log_api",
    obj_list=[log_item],
)
```

Application endpoints should not write directly to `cache_postgres_buffer_log_api`. Middleware owns this buffer so API logs cannot be mixed with ordinary application creates.

See [logs.md](logs.md) for selecting a dedicated logs database.

## Periodic flushing

Lifespan creates one shared lock and one periodic task:

```python
app.state.postgres_buffer_flush_lock = asyncio.Lock()
app.state.postgres_buffer_flush_task = asyncio.create_task(
    app.state.func_postgres_buffer_flush_periodic_task(..., interval_sec=app.state.config_postgres_buffer_flush_auto_sec)
)
```

`func_postgres_buffer_flush_periodic_task` waits `config_postgres_buffer_flush_auto_sec` (default 60s), then calls `func_postgres_buffer_flush_all` for:

```text
client_postgres + cache_postgres_buffer_create
client_postgres_log_api + cache_postgres_buffer_log_api
```

`func_postgres_buffer_flush_all` acquires `postgres_buffer_flush_lock` and invokes `func_postgres_create(mode="flush")` for all active buffers.

The first periodic flush happens after the configured interval (`config_postgres_buffer_flush_auto_sec`). Starting the periodic task does not immediately flush anything.

## Graceful shutdown

Shutdown performs these steps in order:

```text
cancel runtime background tasks
→ cancel postgres_buffer_flush_task
→ final primary-buffer flush
→ final API-log-buffer flush
→ close clients
```

Stopping the periodic task before the final flush prevents periodic and shutdown flushes from overlapping. Primary and API-log final flushes have separate error handling, so one failed destination does not prevent the other from being attempted.

## Reliability and visibility

Buffers are process-local memory, not a durable queue:

- Each application worker or container has its own buffers.
- Buffered records are not visible in PostgreSQL until released or flushed.
- A graceful shutdown attempts a final flush.
- A crash, forced termination, or machine failure can lose pending records.
- A failed insert leaves that buffer group populated for a later attempt while the process remains alive.

Use `mode="buffer"` for records where delayed persistence is acceptable. Use `mode="now"` or a durable queue when persistence must be acknowledged immediately.

---

📚 [PostgreSQL guide](postgres.md) · [API logs](logs.md) · [Back to README](../readme.md)
