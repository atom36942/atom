# ⚡ Performance

Measure first, then change one thing and measure again. Atom spends most request time waiting on Postgres and Redis, so the database is usually the limit before Python is.

## 1. Load Test

Atom's load-test script in `script/` runs many concurrent virtual users against a running server, one route at a time, and prints requests/sec, latency percentiles and error rate.

Run it with the `# command` line at the top of its file.

| Option | Usage |
|---|---|
| `--url` | Server to test (default: `http://localhost:8000`) |
| `--concurrency` | Virtual users per route (default: `50`) |
| `--duration` | Seconds per route (default: `20`) |
| `--route` | Run only this route; repeat for several |
| `--write` | Include routes that create rows (`my-create` inserts into `test`) |
| `--allow-remote` | Allow a non-localhost URL. Use only for a test server, never production |

Routes: `info` (cached), `public-read-cached`, `public-read-db` (cache disabled, real database cost), `my-read` and `my-create`. The `my-*` routes need a test user's access token in `ATOM_LOAD_TOKEN`. Login routes are left out because their rate limits would turn the test into errors.

Reading the report:

- **req/s**: requests handled per second. Higher is better.
- **p50**: half of the requests were faster than this; the typical user.
- **p95 / p99**: the slowest 5% and 1%; problems usually show here first.
- **errors**: failed or timed-out requests. Any errors mean the numbers above them are not trustworthy.

Notes:

- The client runs on the same machine as the server and competes for CPU. Compare runs on the same setup only.
- Every request writes an API log row, so a long test grows `log_api`.
- A large gap between `public-read-cached` and `public-read-db` shows how much the response cache saves.

### Queries per request (CI)
Load test numbers vary between machines and runs, so CI guards what does not vary: the Postgres queries each of Atom's busiest routes sends (login, token refresh, profile, object create, read and update, `/info`), counted exactly on a throwaway database, background work included. A change that adds a query to one of them fails CI with the queries listed; if it is meant, the change updates `BUDGET` in the test (`tests/integration/`) in the same commit.

## 2. Profile With py-spy

[py-spy](https://github.com/benfred/py-spy) samples a running server without code changes and draws a flame graph of where time goes. It is a developer tool and is not in `requirements.txt`.

```bash
pip install py-spy
py-spy record -o profile.svg --pid <server pid> --duration 30
```

Run the load test during the recording, then open `profile.svg`. Wide bars are where the time goes. Time inside `asyncpg` or `redis` means the server is waiting on the database, not on Python. On macOS py-spy needs `sudo`.

## 3. Slow Queries

Enable the `pg_stat_statements` extension on the Postgres server (it must be in `shared_preload_libraries`), then list the slowest queries:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT calls, round(mean_exec_time::numeric, 1) AS mean_ms, round(total_exec_time::numeric) AS total_ms, query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;
```

High `total_ms` queries are the ones worth an index or a rewrite. Use `EXPLAIN ANALYZE` on them.

Without SQL access, admins can read the same report from `GET /admin/postgres-slow-queries` and clear it with `POST /admin/postgres-slow-queries-reset`. See [admin.md](admin.md#5-slow-queries-get-adminpostgres-slow-queries).

## 4. Workers and Pools

- `config_uvicorn_workers` starts that many server processes with `python main.py`. A good starting point is the number of CPU cores. See [config.md](config.md).
- With more than one worker, every `inmemory` cache, rate limit and user check in `config_api` must use `redis` (user checks may also use `realtime` or `token`); startup refuses otherwise.
- Each worker opens its own pools: up to workers × the pools' max sizes added up (`config_postgres_pool_max_size`, or `config_postgres_pool_max_size_<name>` for one database). Startup warns when that can exceed Postgres `max_connections`.
- Start `python main.py` directly. Running `uvicorn main:app --workers N` skips the worker checks and the one-time `tmp/` reset.

## 5. Token Cache

Every request with a token was verified by PyJWT, about 18–34 µs each. `config_token_cache_max` (default `10000` per worker, about 9 MB when full) keeps verified tokens until their own `exp`, so repeat requests take about 0.2 µs. In an A/B load test on one worker, `/info` went from 3,702 to 4,710 req/s (+27%) and `/my/object-read` from 1,946 to 2,302 req/s (+18%). Over the cap, the oldest entry is dropped and its next request is verified again, so speed falls back toward the uncached rate but results never change. Set it to `0` to verify every request: nothing is stored and behaviour matches having no cache (same results, uncached speed). Use `0` while debugging auth, when a project adds token revocation (such as "log out everywhere") and wants every request checked, or on very tight memory. Set it in `config_extend.py` (`config_token_cache_max = 0`) or `.env` (`config_token_cache_max=0`); a negative or non-integer value stops startup.

## 6. FastAPI Telemetry

FastAPI ships native OpenTelemetry support and, by default, checks on every request whether an OpenTelemetry backend is configured (about 2.3 µs). Atom turns it off with `config_is_fastapi_telemetry = False`, which drops that check to about 0.07 µs, roughly a 1% gain. Set it to `True` only when you configure an OpenTelemetry provider.

## 7. ASGI Middleware

The `config_api` middleware in `main.py` is plain ASGI (`app.add_middleware(middleware)`), not `@app.middleware("http")`. The decorator form runs every route in a separate task and copies the response through a stream; plain ASGI runs the route inline and watches the response through a wrapped `send`. In an A/B load test on one worker, `/info` went from 4,924 to 6,564 req/s (+33%), `/public/object-read` from 2,164 to 2,898 (+34%) and `/my/object-read` from 2,302 to 3,096 (+34%); `/info` p99 fell from about 77 ms to about 11 ms. Behaviour notes: only routes with `cache` in `config_api` have their body copied (others, like CSV exports, stream straight through), and only status 200 is stored; security headers are added to every response; the `log_api` row is buffered after the response is sent; an error raised after a response has started is logged but cannot replace it.

## 8. Uvicorn Access Log

uvicorn prints one console line per request by default. Atom already records every request in `log_api` (path, status, IP, timing, error), so `python main.py` turns that line off with `config_is_uvicorn_access_log = False`. In an A/B load test on one worker with uvicorn's default log level (2 alternating rounds), `/info` went from 5,010 to 6,558 req/s (+31%), `/public/object-read` from 2,543 to 2,876 (+13%) and `/my/object-read` from 2,999 to 3,356 (+12%); `/info` p50 fell from 9.6 to 7.5 ms. Startup and error messages still print. Set it to `True` while debugging to watch requests in the console. When starting with `uvicorn main:app` directly, add `--no-access-log` yourself.

## 9. Owner Index and JSON Encoding

**Owner index.** `/my/object-read` runs `WHERE created_by_id = $1 ORDER BY id DESC LIMIT n`. Without an index on the owner column, Postgres walks the table backwards by `id` and discards other users' rows: on a 100,000-row table, a typical user's read scanned 50,000 rows (14 ms). Declaring `"index": "btree(created_by_id,id)"` on the column makes it read only the rows it returns (0.03 ms). In a load test on one worker (20 rows per response), `/my/object-read` went from 1,272 to 4,119 req/s (3.2x) and p50 from 36 to 11 ms. Atom's sample tables `test` and `test_comment` declare it; add the same to every project table read by owner (`btree(received_by_id,id)` for `received_by_id`, and so on). Indexes must be declared in `config_postgres`: startup drops `idx_*` indexes it does not know. On a large existing table, the first startup with a new index builds it and blocks writes to that table while it does.

**JSON encoding.** Routes return through `func_response_json`, which uses orjson. orjson now writes dates itself instead of calling FastAPI's encoder once per date, and Decimal goes through a one-line helper; the output is byte-identical to FastAPI's. Encoding a 20-row response went from 42 to 16 µs, and `/my/object-read` from 3,945 to 4,410 req/s (+12%).

## 10. Route Lookup

FastAPI finds a request's route by checking every route in order, about 0.56 µs per route checked, so a route's cost grows with its position: `/info` (position 2) took 2.4 µs, `/admin/object-read` (60) 35 µs, and project routes, which always come after Atom's, 47–67 µs in a project with 140 routes. `func_app_route_lookup_add` (called once in `main.py`) builds a (method, path) → route table at startup, so a fixed-path route is found with one dict lookup (0.03 µs). Only pairs that FastAPI's own matching resolves to the same route go in the table; static files, websockets, routes with path parameters, 404 and 405 run FastAPI's normal matching, and responses are identical. If a FastAPI upgrade moves the internals it uses, it turns itself off. In an A/B load test on one worker, `/info` went from 12,236 to 12,870 req/s (+5%), `/my/object-read` from 4,461 to 4,891 (+10%) and `/admin/object-read` from 4,326 to 5,108 (+18%); a project route late in the list saves an estimated 25–35%.

## 11. Startup Memory, Blocking Calls and Response Cache

**SDKs load only when configured.** Each `func_client_*` checks its setting before importing its SDK (motor, boto3, openai, google-genai, celery, aiokafka, aio-pika, asyncssh, posthog, Azure, ClickHouse, MSSQL), and `/admin/blob-container-sas` imports the Azure SDK only when it runs. With only Postgres configured, memory after startup fell from 251 MB to 152 MB per worker and startup from about 0.9 s to 0.35 s.

**Blocking SDK calls run in a thread.** boto3 (SES email, SNS SMS, S3 "empty bucket") and Celery `send_task` are synchronous network calls; on the event loop, one OTP email stopped every other request for its whole round trip. They now run through `asyncio.to_thread`, like the Azure and AI calls already did.

**Response cache.** Cached bodies are stored as raw gzip bytes at level 1 under `cache:api:...` keys, instead of base64 text at gzip level 9: storing a 7.5 KB body went from 20 to 8 µs and a cache hit from 4.3 to 3.2 µs, and entries are about 20% smaller. Entries written under the old `cache:` keys are ignored and expire on their own. A hit is sent still gzipped (`Content-Encoding: gzip`) to clients that send `Accept-Encoding: gzip` (browsers and most HTTP clients), so the server skips decompressing it and sends fewer bytes; other clients get it decompressed as before, and cached routes send `Vary: Accept-Encoding`. In an A/B load test on one worker (same server, client header on and off), `/info` (26 KB, 7.5 KB gzipped) went from about 10,000 to 17,300 req/s (+73%, p50 4.5 to 2.8 ms) and a small cached `/public/object-read` from 13,200 to 15,000 (+13%).

**Sentry.** `config_sentry_traces_sample_rate` (default `0.05`) sets the share of requests traced and profiled; every error is still sent. It was 100% of requests before.

**Not adopted, measured:** `hiredis` made each Redis command slower with redis-py's async client (about 72 vs 45 µs per GET), and parsing request bodies with orjson silently turns integers above 64 bits into rounded floats, so both stay out. Skipping asyncpg's connection reset on pool release (a `reset=` no-op) saved one round trip per query and gained only 5–10% on database reads, with worse p95; it would also let session state (a `SET`, a held advisory lock) leak to the next request, so the reset stays.

## 12. Round Trips, Bulk Writes and Compression

Measured on one machine with a local PostgreSQL; on a remote database the saved round trips are worth more.

**One users query per request (3.1).** The role, deactivated and deleted checks share `func_middleware_user_row_reader`: a route with all three in `realtime` mode makes one query instead of three (4,450 vs 1,742 checks/s one at a time; p95 1.1 vs 3.3 ms at 20 concurrent).

**Exports continue after the last id (3.2).** `func_postgres_read_export` sorted by `id` reads each batch with `func_postgres_read(after_id=...)` instead of a growing `OFFSET`: 50,000 rows in 58 vs 137 ms, slowest batch 1.3 vs 4.9 ms, and no repeated or skipped rows while data changes.

**Bulk updates through `unnest` (3.3).** `func_postgres_update` sends each column of simple type as one array joined on `id` instead of a `CASE` per column, which grew with the square of the batch: 1,000 rows in 11.4 vs 24.7 ms.

**Converters built once per call (3.4).** `func_postgres_serialize` works out each column's converter on its first value: 1,000 rows x 5 columns convert in 1.4 vs 8.2 ms; a 1,000-row create 7.6 vs 14.5 ms, update 8 vs 13.7 ms.

**Gzip responses (3.5).** `func_app_gzip_add` gzips responses over 1 KB at level 1 when the client sends `Accept-Encoding: gzip` (browsers always do); already encoded responses (cache hits), event streams and files that are compressed already (images, audio, video, zip, fonts, PDF, Office files; 3.5.1) pass through. 1,000 real rows: 251 KB to 16 KB (quotation, 11 columns) and 738 KB to 54 KB (portal, 26 columns), for 0.4 to 2.6 ms of server time; at 20 Mbit/s the portal page arrives in about 22 instead of 300 ms.

**Startup schema check (3.6).** `func_postgres_schema_init` read each table's columns and indexes separately, dropped every table's triggers and recreated them, one statement at a time and outside a transaction. It now reads the whole catalog once, recreates a trigger only when its definition differs, and applies everything in one transaction. An unchanged start runs 14 queries instead of 98: 13 vs 25 ms on a local database, and 1.0 vs 7.1 s with 70 ms per query (a remote database such as Azure, where Pulse took 7.4 s). Delete guards no longer disappear for other sessions during a start, and an unchanged start takes no table locks.

**No reset query on release (3.7).** asyncpg sent `SELECT pg_advisory_unlock_all(); CLOSE ALL; UNLISTEN *; RESET ALL;` every time a connection went back to the pool, and the request waited for it. `func_client_postgres` pools now skip it: on Pulse's Azure database a one-query request took 61 instead of 102 ms, and login, `/my/object-read` and `/my/object-create` each make one round trip less. An open transaction is still rolled back on release. SQL someone typed (`/admin/postgres-query-runner-*`, pgweb query and stream) runs through `func_postgres_acquire_clean`, which resets that session before it goes back, and the advisory-lock helpers close a connection whose lock cannot be released.

**Creates without a transaction wrapper (3.8).** `func_postgres_create` wrapped every create in `BEGIN`/`COMMIT`, and the bulk insert added a `SAVEPOINT` inside it, although up to 5,000 rows is one `INSERT`, all-or-nothing by itself. It now opens a transaction only when a create spans several `INSERT`s and none is open yet. At 50 ms per query: 1 row 52 vs 155 ms, 10 rows 52 vs 258 ms, 1,000 rows 62 vs 269 ms (1 round trip instead of 3 or 5). A failed create still saves no row, in one statement or across several.

**Updates and deletes without a transaction wrapper (3.9).** `func_postgres_update` and `func_postgres_delete` follow the 3.8 rule: one `UPDATE` or `DELETE` statement runs alone, several share one transaction, and a caller's own transaction gets no savepoint. Measured on an Azure PostgreSQL database (Atom's `test` table): update 10 rows 48 vs 143 ms, update 1,000 rows 146 vs 233 ms, delete 2 rows 51 vs 140 ms. The 3.8 creates on the same table: 1 row 48 vs 142 ms, 10 rows 49 vs 238 ms, 1,000 rows 108 vs 303 ms.

**Page files kept by the browser (3.10).** Pages (`/` and `/page/<name>`) are served through `func_app_page_response`, which stamps every `src`/`href` to `/static/<file>` with `?v=<fingerprint of that file>` (worked out once per file, redone when the file changes). A stamped file is sent with `Cache-Control: public, max-age=31536000, immutable` only when its `?v=` is this server's fingerprint of the file (during a rolling deploy an older instance answers the new link with `no-cache`, so no browser keeps an old file under a new address); the page itself and unstamped files still revalidate every load. In the browser, a second load of a page with three local files sent one request (the page, 304) instead of four. Each revalidation it saves cost about 50 ms on a warm connection and 150 ms on a new one (measured on a deployed Atom app on Azure).


**pgweb in one round trip per action (3.10.2).** The table list reads the database name, server version and each table's primary key in one query. Opening a table reads its columns and its first page at the same time (the pgweb pool keeps two connections open); the key it guessed from the list is checked against the columns, and the page is read again only when the key changed. Later pages and filters reuse the column types read when the table opened, instead of looking each one up. A reload asks for the table list and the open table together. On Pulse's Azure database (one round trip 47 ms): table list 55 vs 102 ms, opening a table 70 vs 119 ms, next page 67 vs 112 ms, filter 65 vs 115 ms, reload with a table open 69 vs 207 ms.

**Request size limits (3.11).** Atom read a request body of any size into memory before checking it, and parsing JSON takes several times its size: one 300 MB body sent to a public route without a token raised the server from 103 MB to 1,403 MB. `func_middleware_body_limit` now refuses a body over `config_request_body_max_kb` (10 MB) or, for multipart uploads, `config_request_form_max_kb` (100 MB) with `413`: a declared `Content-Length` before any of it is read, a body without one as it arrives. The same 300 MB request now gets `413` in 0.3 s and the server stays at 170 MB.

**Response cache size cap (3.12).** The `inmemory` API response cache dropped entries only when they expired, so a route caching large responses per user or per query could grow until the next cleanup. `config_api_cache_inmemory_max_kb` (100 MB per worker, counting the stored gzipped bodies) now drops the oldest entries when a new one would pass it; counting the size costs about 0.5 ms per cache write at 10,000 entries, and only on a miss.

**Activity written once per 5 minutes (3.12.2).** `/my/profile` (in the background) and `/my/ping` wrote `users.last_active_at` on every call, so every page open by every user wrote a new row version of `users`, ran its row triggers and moved `updated_at`. `func_user_last_active_update` now writes only when the stored time is over 5 minutes old, and a table with `last_active_at` gets `func_set_updated_at_except_activity`, which leaves `updated_at` alone when only `last_active_at` changed. 1,000 page opens by one user (local database): 0.21 vs 0.31 ms each, 1 KB vs 259 KB of WAL.

**RAM history (3.13).** `func_memory_history_periodic_task` reads the worker's RSS once a minute (one `psutil` call, a few microseconds) and keeps the last 1,440 readings (24 hours, about 200 KB), for the monitor's RAM-over-time chart. `/info` answered in 0.49 ms on average with it running.

**One export path for every database (4.0).** Every CSV export, Atom's routes and every project's, goes through `func_postgres_export` (or `func_mssql_export`, `func_clickhouse_export`): one query read with a cursor in a read-only transaction and streamed in 64 KB chunks, capped by `config_export_limit` (1,000,000). The table export no longer pages with `OFFSET` for sorts other than `id`. 1,000,000 rows of four columns (local database): 3.9 s, a 77 MB file, first bytes after 1 ms, process memory at 83 MB throughout.
