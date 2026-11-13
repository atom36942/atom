# 🏁 Benchmark

Two kinds of numbers, measured with Atom's default settings unless a row says otherwise:

- **Local** (sections 1–7): one laptop with a fresh local database, which shows what Atom itself costs. Atom 7.1.0, and 7.1.1 for the Redis pool and comparison rows.
- **Remote** (section 8): a real cloud deployment called over the internet, which shows what users actually wait for. Atom 8.0.0.

Each run was warmed up first and repeated. How to check any of these numbers yourself is at the end of the page.

| | |
|---|---|
| Machine | Apple M5 (4 performance + 6 efficiency cores), 24 GB, macOS 26.6 |
| Stack | Python 3.14.9, FastAPI 0.162.0, uvicorn 0.54.0, asyncpg 0.32.0, PostgreSQL 18.3, Redis 8.6.2 |
| Data | Atom's `test` table: 1,000,000 rows (683 MB), then 10,000,000 rows (6.2 GB); 1,000 users |
| Load | [oha](https://github.com/hatoo/oha) on the same machine, 3 s warm-up, then 12–30 s per run; "req/s" is the median of 3–4 alternating runs for comparisons |
| Default run | 1 worker, Postgres pool of 10, 50 concurrent users, 20 rows per read, `log_api` on |

## 1. Headline

| What | Result |
|---|---|
| Cached route, 4 workers | **23,626 req/s**, p50 4.1 ms |
| Database read / create, 1 worker | **2,561 / 4,429 req/s**, p50 8 / 5 ms |
| 1,000 concurrent users, 4 workers | **20,468 cached req/s**, **7,326 reads/s**, **10,665 creates/s**, 0 errors |
| Same features as hand-written FastAPI + asyncpg, local database | even: 2,643 vs 2,865 reads/s, 4,442 vs 4,176 creates/s |
| Database 50 ms away | **2× hand-written FastAPI, 3× SQLAlchemy**: 55 ms per request (108 ms, 163 ms), one round trip |
| 10,000,000 rows vs 1,000,000 | same speed: 2,717 vs 2,675 reads/s; page at row 9,000,000 in **0.87 ms** |
| Export 1,000,000 rows (17 columns, 269 MB CSV) | 10.6 s, first byte after **2 ms**, server memory **+1 MB** |
| Response size, 1,000 rows | 327 KB → **9 KB** gzipped |
| A 300 MB request body | refused with `413` in **55 ms**; server memory stays at 175 MB |
| Startup, memory | first answer after **0.77 s**; **164 MB** per worker |
| Real cloud, 1 worker, over the internet | read or create in **56–59 ms**, of which about 4 ms is the server; **260 reads/s** and **355 creates/s** with 0 errors |

## 2. Workers

Shared state in Redis (needed for more than one worker), 100 concurrent users.

| Route | 1 worker | 2 workers | 4 workers | 8 workers |
|---|---|---|---|---|
| `/info` (cached) | 8,119 | 14,109 | **23,626** | 19,121 |
| `/public/object-read` (cached) | 7,611 | 14,157 | 21,407 | **22,905** |
| `/public/object-read` (database) | 2,662 | 5,236 | 6,657 | **6,830** |
| `/my/object-read` (token, owner index) | 2,544 | 5,037 | **6,460** | 5,939 |
| `/my/object-create` | 4,419 | 7,874 | 6,986 | **11,656** |

Throughput grows almost linearly up to the 4 performance cores; beyond that, the load client and Postgres compete for the same CPU.

## 3. Compared with other stacks

The same two endpoints (read the caller's 20 newest rows, insert one row) on 1 worker with a pool of 10, written four ways. The fair comparison is the hand-written FastAPI app that does the same work per request as Atom:

| Stack | Work per request |
|---|---|
| **Atom** | its normal `/my/object-read` and `/my/object-create` |
| **FastAPI + asyncpg, same features** | JWT check, validated params (table and order allow-lists, limit bounds, pydantic body), owner filter, request id and security headers, gzip over 1 KB, one API log row per request buffered and written 100 at a time; written the efficient way (plain ASGI middleware, orjson, `COPY` for the log) |
| FastAPI + asyncpg, no features | JWT check and the query only: the floor for Python, not a real app |
| FastAPI + SQLAlchemy 2 async ORM, no features | JWT check and the ORM query only |

Median of 3 alternating rounds, 50 users; "50 ms away" puts toxiproxy (25 ms each way) between the app and Postgres, about like a cloud database:

| Stack | Reads/s | Creates/s | One read, database 50 ms away | Reads/s, database 50 ms away |
|---|---|---|---|---|
| **Atom** | 2,643 | **4,442** | **55 ms** | **182** |
| FastAPI + asyncpg, same features | **2,865** | 4,176 | 108 ms | 94 |
| FastAPI + asyncpg, no features | 3,507 | 5,224 | 107 ms | 94 |
| FastAPI + SQLAlchemy, no features | 727 | 2,049 | 163 ms | 63 |

- **Local database, same features:** Atom and hand-written FastAPI are even, within 8% either way (FastAPI reads +8%, Atom creates +6%). The no-features app is the price of the features themselves, which any real app pays.
- **Database 50 ms away:** Atom is **2× faster** than hand-written FastAPI, with or without features, and **3×** faster than SQLAlchemy, because Atom makes one round trip per request. asyncpg's pool sends a reset query when a connection goes back (2 round trips), and SQLAlchemy wraps the query in `BEGIN` and `COMMIT` (3). Atom skips the reset and the transaction around single statements, and the gap grows with the distance to the database.
- **Tail latency:** up to 8.0.1 Atom's p95 at 50 local users was higher (46 ms vs ~20 ms) at the same throughput: connections released without a reset query went to new requests ahead of waiting ones. Since 8.0.2 they go in the order asked: p95 18 ms at 50 users (creates 30 → 13 ms) and 91 ms instead of 242 ms at 200 users, throughput within 4%, a single request unchanged (0.76 ms).

## 4. Techniques, each on and off

Each pair was measured on one worker, in alternating runs.

| Technique | Off | On | Gain |
|---|---|---|---|
| Owner index `btree(created_by_id,id)`, a user whose 100 rows are the oldest of 1M | 61 req/s, p50 813 ms (query 120 ms) | 2,523 req/s, p50 8.7 ms (query 0.06 ms) | **41×** |
| Response cache on `/public/object-read` | 2,675 req/s | 8,040 (redis) / **11,792** (inmemory) | **4.4×** |
| Cursor paging instead of OFFSET, row 9,000,000 of 10M (SQL) | 3.2–9.2 s | 0.05 ms | **>60,000×** |
| Redis pool that waits for a free connection, `/info` cached in Redis, 1,000 users, 4 workers | 11,378 req/s, 28% `503`, p99 144 ms | 20,468 req/s, 0 errors, p99 93 ms | **1.8×**, no errors |
| Buffered creates (`mode=buffer`, 100 users) | 4,429 req/s, p95 76 ms | 5,674 req/s, p95 17.6 ms | **+28%**, p95 4.3× lower |
| Route lookup table | 2,347 req/s | 2,561 req/s | **+9%** |
| gzip, `/info` / 100 rows / 1,000 rows | 26.7 / 32.8 / 327 KB | 7.6 / 1.2 / 9.2 KB | **3.5× / 28× / 35×** smaller |
| Streamed export, 1M rows | — | +1 MB server memory | constant memory |
| Body size limit, 300 MB body | — | `413` in 55 ms, +1–11 MB | never read into memory |

What some optional settings cost on `/my/object-read`:

| Setting | req/s | vs default (2,561) |
|---|---|---|
| `config_is_log_api=false` | 2,814 | +10% |
| Role, deactivated and deleted checks in `token` / `inmemory` mode | 2,594 / 2,592 | free |
| The same checks in `realtime` mode (one query for all three) | 2,370 | −7% |
| The same checks in `redis` mode | 2,026 | −21% |

## 5. Data size

| | 1,000,000 rows | 10,000,000 rows |
|---|---|---|
| `/public/object-read` from the database, req/s | 2,675 | 2,717 |
| `/my/object-read`, user with old rows, req/s | 2,523 | 2,522 |
| `/my/object-create`, req/s | 4,429 | 4,416 |

Paging `/admin/object-read` with 50 rows per page on 10M rows, one request at a time:

| Position | Cursor (`after`) | Page number (`page`, OFFSET) |
|---|---|---|
| Row 0 | 0.81 ms | 0.77 ms |
| Row 10,000 | 0.81 ms | 3.38 ms (page 200, the last one `page` allows) |
| Row 1,000,000 | 0.88 ms | refused: `page` stops at 10,000 rows |
| Row 9,000,000 | 0.87 ms | refused (3.2 s or more in plain SQL) |

## 6. One request at a time

Median of 30 requests (bulk: 7 local, 5 remote) on the 10M table. "Remote" means the database is 50 ms away.

| Request | Local | Remote |
|---|---|---|
| `/my/object-read`, 20 rows | 0.72 ms | 56 ms |
| `/my/object-create`, 1 row | 0.70 ms | 56 ms |
| create / update / delete 10 rows | 1.2 / 1.1 / 0.7 ms | 56 / 56 / 55 ms |
| create / update / delete 100 rows | 4.5 / 4.7 / 1.1 ms | 65 / 62 / 56 ms |
| create / update / delete 1,000 rows | 33 / 33 / 4.2 ms | 85 / 85 / 59 ms |
| Login (argon2 password check + 1 query) | 50 ms | 105 ms |
| Startup to first answer | 0.77 s | 3.5 s |

## 7. Queue

`POST /my/object-create?queue=redis` with 100 users. The API accepts each create and answers at once; one `consumer_redis` process writes the rows.

| | Result |
|---|---|
| API accepted | 3,508 req/s, p50 27 ms, 0 errors |
| One consumer wrote | 2,468 rows/s (70,241 rows in 28.5 s) |

## 8. Remote: a real cloud deployment

An Atom app on a cloud app service (1 worker) with a managed PostgreSQL 16 in the same region, called from a laptop over the internet about 50 ms away. The `test` table held 200,000 rows. Server time is `log_api.response_time_ms`: what Atom spent, without the internet.

One request at a time (median of 30; bulk writes 7):

| Request | Total | Server |
|---|---|---|
| `/my/object-read`, 20 rows | 56 ms | 4 ms at low load |
| `/my/object-create`, 1 row | 59 ms | |
| create / update / delete 10 rows | 65 / 68 / 56 ms | |
| create / update / delete 100 rows | 100 / 108 / 56 ms | |
| create / update / delete 1,000 rows | 166 / 184 / 62 ms | |
| Cursor page at row 0 / row 100,000 | 58 / 57 ms | |
| Export 100,000 rows (27 MB CSV) | 7.6 s, first byte after 171 ms | 4.0 s |
| Login (argon2 password check) | 432 ms | 231 ms |

The internet takes about 52 ms of every request, so what the server adds is small and stays the same at row 100,000 as at row 0.

Load, 20 s per run, 0 errors in every run:

| Users | `/info` (cached) | `/my/object-read` | `/my/object-create` |
|---|---|---|---|
| 10 | 188 req/s, p50 51 ms | 173 req/s, p50 54 ms | 168 req/s, p50 55 ms |
| 25 | 463 req/s, p50 52 ms | 269 req/s, p50 90 ms | 353 req/s, p50 67 ms |
| 50 | 853 req/s, p50 56 ms | 255 req/s, p50 140 ms | 355 req/s, p50 130 ms |

At 10 users every route is limited by the internet (10 users ÷ 56 ms ≈ 180 req/s). From 25 users on, one cloud worker settles at about **260 reads/s and 355 creates/s**; the cached route keeps growing with the number of users. This was a small cloud plan: its one worker does about a tenth of the laptop's (section 3), so more workers or a bigger plan is where more throughput comes from.

## 9. Check it yourself

1. Start a separate PostgreSQL 18 and Redis (not your project's); this run used `shared_buffers=2GB`, `work_mem=32MB`, `max_connections=300`. Point `config_postgres_url_master` and `config_redis_url_*` at them and start Atom once so it creates its tables.
2. Load data with plain SQL. Owners are spread like real users: `insert into test (created_by_id, title, ...) select 3 + g % 1000, 'title ' || g, ... from generate_series(1, 1000000) g`, then `vacuum analyze test`.
3. Create a role 2 user with `/admin/user-create`, log in, and use the token for the `/my/*` routes.
4. Load: `oha -z 15s -c 50 -H "authorization: Bearer <token>" -H "accept-encoding: gzip" "http://127.0.0.1:8000/my/object-read?table=test&limit=20"`. Warm up for 3 s first, run each comparison 3 times or more in alternating order, and take the median. Run `vacuum analyze test` after deleting rows: autovacuum running mid-test moved results by 15%.
5. On/off comparisons change one setting through `.env` or `config_extend.py` (for example, every `inmemory` mode switched to `redis` for more than one worker), or drop one index, then restore it.
6. Database 50 ms away: `toxiproxy-cli create -l 127.0.0.1:5433 -u 127.0.0.1:5432 pg`, then add a `latency=25` toxic upstream and downstream, and point Atom at port 5433.
7. Baselines: one FastAPI file each, with the same JWT check and query, a pool of 10 and the same uvicorn settings. The same-features app adds what Atom does per request (section 3): param validation, request id, security headers, gzip and a buffered API log.
8. Remote: deploy an Atom app with one worker, load rows into `test` with SQL, warm it up, then run the same `oha` commands against its URL with an admin token, keeping one connection open per user. Read the server time from `log_api`, then delete the `test` rows and the benchmark's `log_api` rows.
