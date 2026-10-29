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
- Each worker opens its own pools: up to workers × pools × `config_postgres_pool_max_size` connections. Startup warns when that can exceed Postgres `max_connections`.
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
