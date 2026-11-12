# 🏁 Benchmark

Every number on this page was measured on one laptop with a fresh local database, using Atom 7.1.0 (7.1.1 for the Redis pool rows) with its default settings unless a row says otherwise. Each run was warmed up first and repeated. How to check any of these numbers yourself is at the end of the page.

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
| One request, cloud-like database (50 ms away) | **56 ms**: one round trip (FastAPI + asyncpg 107 ms, FastAPI + SQLAlchemy 160 ms) |
| 10,000,000 rows vs 1,000,000 | same speed: 2,717 vs 2,675 reads/s; page at row 9,000,000 in **0.87 ms** |
| Export 1,000,000 rows (17 columns, 269 MB CSV) | 10.6 s, first byte after **2 ms**, server memory **+1 MB** |
| Response size, 1,000 rows | 327 KB → **9 KB** gzipped |
| A 300 MB request body | refused with `413` in **55 ms**; server memory stays at 175 MB |
| Startup, memory | first answer after **0.77 s**; **164 MB** per worker |

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

The same endpoint (verify the JWT, read the caller's 20 newest rows, or insert one row) written three ways, with 1 worker and a pool of 10 each. The baselines do only that; Atom also runs its policy middleware, parameter validation and API log.

| Stack | Read req/s | Create req/s | One read, database 50 ms away | Reads/s, database 50 ms away |
|---|---|---|---|---|
| **Atom** | 2,642 | 4,573 | **56 ms** | **171** |
| FastAPI + raw asyncpg | **4,479** | **5,720** | 107 ms | 94 |
| FastAPI + SQLAlchemy 2 async ORM | 802 | 2,221 | 160 ms | 63 |

- **Local database:** Atom is 3.3× faster than SQLAlchemy on reads and 2.1× faster on creates, and reaches 59–80% of hand-written asyncpg.
- **Database 50 ms away** (toxiproxy, 25 ms each way, about like a cloud database): Atom is fastest, 1.8× hand-written asyncpg and 2.7× SQLAlchemy. Atom makes one round trip per request: it skips asyncpg's reset query on release and the `BEGIN`/`COMMIT` around single statements. SQLAlchemy makes three.

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

## 8. Check it yourself

1. Start a separate PostgreSQL 18 and Redis (not your project's); this run used `shared_buffers=2GB`, `work_mem=32MB`, `max_connections=300`. Point `config_postgres_url_master` and `config_redis_url_*` at them and start Atom once so it creates its tables.
2. Load data with plain SQL. Owners are spread like real users: `insert into test (created_by_id, title, ...) select 3 + g % 1000, 'title ' || g, ... from generate_series(1, 1000000) g`, then `vacuum analyze test`.
3. Create a role 2 user with `/admin/user-create`, log in, and use the token for the `/my/*` routes.
4. Load: `oha -z 15s -c 50 -H "authorization: Bearer <token>" -H "accept-encoding: gzip" "http://127.0.0.1:8000/my/object-read?table=test&limit=20"`. Warm up for 3 s first, run each comparison 3 times or more in alternating order, and take the median. Run `vacuum analyze test` after deleting rows: autovacuum running mid-test moved results by 15%.
5. On/off comparisons change one setting through `.env` or `config_extend.py` (for example, every `inmemory` mode switched to `redis` for more than one worker), or drop one index, then restore it.
6. Database 50 ms away: `toxiproxy-cli create -l 127.0.0.1:5433 -u 127.0.0.1:5432 pg`, then add a `latency=25` toxic upstream and downstream, and point Atom at port 5433.
7. Baselines: one FastAPI file each, with the same JWT check and query, a pool of 10 and the same uvicorn settings.
