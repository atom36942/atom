# ⚡ Performance

Measure first, then change one thing and measure again. Atom spends most request time waiting on Postgres and Redis, so the database is usually the limit before Python is.

## 1. Load Test

[`script/load_test.py`](../script/load_test.py) runs many concurrent virtual users against a running server, one route at a time, and prints requests/sec, latency percentiles and error rate.

```bash
venv/bin/python -m script.load_test --concurrency 50 --duration 20
```

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
