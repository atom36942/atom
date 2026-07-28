# Admin Toolkit

The `/admin/*` endpoints ([`router/admin.py`](../router/admin.py)) are the operator's control panel: run SQL, generate queries with AI, import data, inspect schema, manage storage, and refresh caches. **All are role-restricted** (mostly role `1`, some `1`+`2`) via `config_api` — see [security.md](security.md).

---

## Query runners

Run arbitrary SQL against Postgres or MSSQL. Body: `{"sql": "...", "db": "main"|"external"}` (Postgres).

| Endpoint | Purpose |
|----------|---------|
| `POST /admin/postgres-query-runner-read` | Run a read query; capped at `config_query_runner_read_limit` rows. |
| `POST /admin/postgres-query-runner-write` | Run a write query (INSERT/UPDATE/DDL). **Blocked on `db=external`.** |
| `POST /admin/postgres-query-runner-read-export` | Stream results as a CSV download (cap `config_query_runner_export_limit`). |
| `POST /admin/mssql-query-runner-read` / `-write` / `-read-export` | Same, against MSSQL. |

```bash
curl -X POST http://localhost:8000/admin/postgres-query-runner-read \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT role, count(*) FROM users GROUP BY role"}'
```

Read runners target `client_postgres_read_fallback` (or the external pool); writes require the primary. Export endpoints return a `StreamingResponse` (`text/csv`), so results never fully materialize in memory.

> These execute raw SQL — they are powerful and intentionally admin-only. Keep them behind `realtime` role checks in production.

---

## AI query generator

`POST /admin/postgres-query-generator-ai` — turn a natural-language question into SQL.

```jsonc
{"question": "top 10 users by number of objects created", "ai": "gemini", "db": "main"}
```

- `ai` selects the provider from `config_ai_services` (`gemini` default, or `openai`); requires the corresponding key.
- It feeds the AI an **AI-oriented schema snapshot** (`cache_postgres_schema_ai`, built at startup) so generated SQL matches your real tables.
- Returns the generated query — pair it with the read runner to execute.

---

## Data imports

Upload a file (multipart form) to bulk-load data. `mode` selects the operation.

| Endpoint | Target | Modes |
|----------|--------|-------|
| `POST /admin/postgres-import` | A Postgres `table` | `create` / `update` / `delete` |
| `POST /admin/redis-import` | Redis (TTL `config_redis_cache_ttl_sec`) | `create` / `delete` |
| `POST /admin/mongodb-import` | A Mongo `database` + `table` | `create` / `update` / `delete` |

```bash
curl -X POST http://localhost:8000/admin/postgres-import \
  -H "Authorization: Bearer <admin-token>" \
  -F "mode=create" -F "table=test" -F "file=@./rows.csv"
```

---

## Schema & introspection

| Endpoint | Returns |
|----------|---------|
| `GET /admin/postgres-info?db=main` | DB size/health/stats (`func_postgres_info_read`). |
| `GET /admin/postgres-schema?db=main` | Live schema (tables, columns, indexes). |

Both accept `db=main` (default) or `db=external`, and are cached (`api_cache_sec`).

---

## Object CRUD (unrestricted)

`/admin/object-create`, `-read`, `-update`, `-delete` mirror the generic CRUD engine (see [crud.md](crud.md)) but **without ownership scoping** — an admin can operate on any row of any table. Extra guards still apply: user hard-delete needs `config_is_enable_user_delete=1`; updating `users` email/mobile can require OTP (`config_is_enable_otp_require_users_update`); password updates must be `{id, password}` only.

---

## Storage management

`/admin/blob-container-read`, `/admin/blob-container-ops` (`create`/`public`/`empty`/`delete`), and `/admin/blob-delete-url` manage buckets/containers and objects directly. See [blob.md](blob.md).

---

## Cache refresh — `GET /admin/sync`

Flushes the write buffer and **rebuilds every in-memory cache** live — schema, AI schema, external schema, table/column lists, OpenAPI spec, config, and the user role/deactivated/deleted maps. Run it after changing the schema or `config` table so the running server picks up changes **without a restart**. (This is the runtime twin of what the lifespan does at startup — see [lifespan.md](lifespan.md).)

---

📚 [Back to README](../readme.md)
