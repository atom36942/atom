# TimescaleDB

For high-volume time-series data: GPS, IoT sensors, metrics, events. TimescaleDB is a PostgreSQL extension, so Atom connects to it like any Postgres database: no new client or driver. The schema lives in `config_extend.py` as `config_postgres_schema_<name>`, and Atom applies it at every startup, like master's. Everything below is general: create as many hypertables, rollups and policies as a feature needs. The examples use the database `telematics` and a `gps_point` table (one location per device per timestamp).

## Main steps

A guideline, not a fixed recipe: adapt it to the feature.

1. **Server.** PostgreSQL with the TimescaleDB **Community** edition. `shared_preload_libraries = 'timescaledb'`, then `timescaledb-tune`. Check: `SHOW timescaledb.license;` returns `timescale`. Some managed services ship only the **Apache** edition (`apache`): hypertables work, compression, policies and rollups don't; see [Apache edition](#apache-edition-managed-services) for what to use instead.
2. **Database and user.** An empty database, and a user that owns its `public` schema (Atom creates the tables). Extensions the user may not create (managed services: allow-list them first) are created once by an admin: `CREATE EXTENSION IF NOT EXISTS timescaledb;` (plus `postgis` for locations); Atom skips one it can't create, with a warning.
3. **Connect.** One `.env` line; the name after `config_postgres_url_` is the database's name everywhere in Atom.
   ```
   config_postgres_url_telematics=postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require
   ```
   Atom opens the pool at startup and the app gets it as `app_state.client_postgres_dict["telematics"]` ([database.md](database.md)).
4. **Schema.** In `config_extend.py`, `config_postgres_schema_telematics` with the same name: tables in `table` (Atom creates them, adds new columns, indexes and checks), hypertables, compression, policies and rollups in `sql` (run after the tables, at every startup), built from the [samples](#samples). Nothing of Atom's goes there: `users`, logs and the rest stay on master.
   ```python
   config_postgres_schema_telematics = {
   "table": {
   "gps_point": {"column": [
   {"name": "device_id", "datatype": "bigint", "is_primary_key": True},
   {"name": "time", "datatype": "timestamptz", "is_primary_key": True},
   {"name": "lat", "datatype": "float8", "is_not_null": True},
   {"name": "lng", "datatype": "float8", "is_not_null": True},
   {"name": "speed", "datatype": "real"},
   ]},
   "gps_point_latest": {"column": [
   {"name": "device_id", "datatype": "bigint", "is_primary_key": True},
   {"name": "time", "datatype": "timestamptz", "is_not_null": True},
   {"name": "location", "datatype": "geography(Point,4326)", "is_not_null": True, "index": ["gist(location)"]},
   {"name": "speed", "datatype": "real"},
   ]},
   },
   "control": {"extension": ["timescaledb", "postgis"], "buffer_limit": {"gps_point": 1000}},
   "sql": {"gps": [
   "SELECT create_hypertable('gps_point', by_range('time', INTERVAL '7 days'), if_not_exists => true)",
   "SELECT add_retention_policy('gps_point', INTERVAL '1 year', if_not_exists => true)",
   ]},
   }
   ```
   `gps_point` has no `id`: a point is device + time, and the key must include `time`. `lat`/`lng` as plain numbers compress far better than a geography column.

   **Access.** Nothing is listed in `control`, so `/public`, `/private` and `/my` refuse both tables (403), and only users whose `master.users.permissions` hold an admin read route's id reach them (`GET /admin/object-read?connection=telematics&table=gps_point&order=time desc`; root holds every id). To let any logged-in user read the live table, add `"private_read": ["gps_point_latest"]` to this `control`. The feature's own routes need nothing there. `/admin/object-create` can write points by hand; `/my` and `/public` creates need a `created_by_id` column, so device points are written by the feature's code with `func_postgres_create` ([below](#points-from-a-device-webhook)).

   **Retention.** `control.retention_day` deletes by a `created_at` column (startup refuses a table without one, such as `gps_point`); on a hypertable `add_retention_policy` (or a scheduled `drop_chunks`) in `sql` drops whole chunks, much faster.
5. **Start Atom.** It applies the schema to that database (master first), then reads it into the schema cache. Before a deploy, `venv/bin/python -m script.postgres_schema_plan --db telematics` shows what the next start would change.
6. **APIs.** The feature's own `function_extend/gps.py` (`func_gps_*` with the SQL), `router_extend/gps.py` (reads params, calls one function) and a `config_api` entry per route in `config_extend.py`, as for any feature ([extend.md](extend.md)).
7. **UI.** A page in `static_extend/gps/` that calls those APIs (map, charts, reports), built to [frontend.md](frontend.md); business rules in `docs_extend/gps.md`, tests in `tests_extend/test_gps.py`.

A route on the new pool, for example:
```python
# function_extend/gps.py
async def func_gps_route_read(*, client_postgres, device_id: int, start, end) -> list:
    rows = await client_postgres.fetch("SELECT time, lat, lng, speed FROM gps_point WHERE device_id = $1 AND time >= $2 AND time < $3 ORDER BY time", device_id, start, end)
    return [dict(r) for r in rows]

# router_extend/gps.py
@router.get("/gps/route")
async def func_api_gps_route(*, request: Request):
    app_state = request.app.state
    p = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "device_id", "type": "int", "required": True}, {"name": "start", "type": "str", "required": True}, {"name": "end", "type": "str", "required": True}], strict=True, strict_types=True, reject_unknown=True)
    rows = await app_state.func_gps_route_read(client_postgres=app_state.client_postgres_dict["telematics"], device_id=p["device_id"], start=datetime.fromisoformat(p["start"]), end=datetime.fromisoformat(p["end"]))
    return {"status": 1, "message": rows}
```

## Standard practices

| Practice | Why |
|---|---|
| A separate database, `config_postgres_url_<name>`, named for what it holds | Heavy time-series load stays off `master`; the pool can be sized alone (`config_postgres_pool_max_size_<name>`) |
| Its schema only in `config_postgres_schema_<name>` | One source of the schema, reviewed with the code, applied at every start; never change the database by hand |
| Tables in `table`, TimescaleDB objects in `sql` | Atom manages columns, indexes and checks; hypertables, compression, policies and rollups are TimescaleDB calls |
| A key that includes the time column, no `id` | A hypertable's primary and unique keys must include its time column; `id` is optional in Atom |
| Every `sql` statement safe to run again ([forms below](#safe-to-run-again)) | `sql` runs at every startup; what is already there is skipped |
| The feature's own routes for reports, maps and writes | Atom's generic routes read a table without `id` (with an `order`), but can't update, delete or relation-fetch it, and only admin creates in a table without `created_by_id` |
| Compression and retention from the first day | Raw points grow fast; old chunks shrink about 90% and expire without a slow `DELETE` (Apache edition: retention by a scheduled `drop_chunks`, disk sized for uncompressed data) |
| Every read filters on the time column | Only the chunks in range are read |
| Rollups for reports, a `<table>_latest` table for live views | Long ranges and live maps without scanning raw points |
| Batched writes with `ON CONFLICT DO NOTHING` | One round trip per batch; a retried batch is not written twice ([from a webhook](#points-from-a-device-webhook): `mode="buffer"`, `on_conflict="nothing"`) |

**On `master` instead** (no separate database): skip steps 2 and 3, and put the tables and statements in `config_postgres_schema_master` in `config_extend.py`.

## Safe to run again

`sql` runs at every startup, after the tables, so each statement must do nothing when its object is already there. Put one statement per list item: `"sql": {"<feature>": ["<statement 1>", "<statement 2>", …]}` (on master: `{**base_config_postgres_schema_master["sql"], "<feature>": [...]}`). Each runs on its own, and a continuous aggregate can't be created inside a multi-statement string.

| Object | Safe form |
|---|---|
| Table, column, index | in `table`: Atom creates what is missing (a new column is added on the next start) |
| Hypertable | `create_hypertable(…, if_not_exists => true)` |
| Compression settings | inside `DO $$ … IF NOT EXISTS (… compression_enabled) …` (sample below) |
| Policies | `add_compression_policy / add_retention_policy / add_continuous_aggregate_policy(…, if_not_exists => true)` |
| Rollup | `CREATE MATERIALIZED VIEW IF NOT EXISTS … WITH NO DATA` |

`if_not_exists` keeps what is there: a changed interval in the config is not applied. To change a policy or chunk size, run `remove_<kind>_policy(…)` or `set_chunk_time_interval(…)` once by hand, then update the config. A column type change on a compressed hypertable fails: decompress first, or add a new column.

## Samples

The SQL behind each part. Tables go in `table` (the `CREATE TABLE` below shows what Atom creates from it); the other statements go in `sql`, one per list item.

**Table, then hypertable.** A normal table, then split into chunks by time. Chunk size: about a week of data for a few thousand rows a minute; smaller (1 day) when a chunk with its indexes would pass a quarter of the server's memory.
```sql
CREATE TABLE IF NOT EXISTS gps_point (
  time       timestamptz NOT NULL,       -- the device's timestamp
  device_id  bigint NOT NULL,
  lat        double precision NOT NULL,
  lng        double precision NOT NULL,  -- plain numbers compress far better than a geography column
  speed      real,                       -- km/h
  PRIMARY KEY (device_id, time)          -- no id: a point is device + time; keys must include time
);
SELECT create_hypertable('gps_point', by_range('time', INTERVAL '7 days'), if_not_exists => true);
SELECT set_chunk_time_interval('gps_point', INTERVAL '1 day');   -- later, if needed; applies to new chunks only
```

**Compression.** Old chunks turn columnar, often 90% smaller; queries are unchanged. `segmentby` = the column most reads filter on.
```sql
DO $$ BEGIN    -- settings once: changing them after chunks are compressed fails
  IF NOT EXISTS (SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = 'gps_point' AND compression_enabled) THEN
    ALTER TABLE gps_point SET (timescaledb.compress, timescaledb.compress_segmentby = 'device_id', timescaledb.compress_orderby = 'time DESC');
  END IF;
END $$;
SELECT add_compression_policy('gps_point', INTERVAL '7 days', if_not_exists => true);   -- compress chunks older than 7 days
-- by hand: SELECT compress_chunk(c, if_not_compressed => true) FROM show_chunks('gps_point', older_than => INTERVAL '7 days') c;
-- to edit old data in bulk: SELECT decompress_chunk(c, if_compressed => true) FROM show_chunks('gps_point', older_than => INTERVAL '7 days') c;
```

**Retention.** Nothing expires until a policy is added; it drops whole chunks (instant, no slow `DELETE`).
```sql
SELECT add_retention_policy('gps_point', INTERVAL '1 year', if_not_exists => true);
-- change: SELECT remove_retention_policy('gps_point'); then add it again
-- by hand: SELECT drop_chunks('gps_point', older_than => INTERVAL '1 year');
```

**Rollup (continuous aggregate).** A materialized view TimescaleDB keeps up to date, for dashboards and reports over long ranges without reading every raw point.
```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS gps_point_hourly
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS    -- false: includes not-yet-refreshed recent rows
SELECT time_bucket('1 hour', time) AS bucket, device_id, count(*) AS points, avg(speed) AS avg_speed, max(speed) AS max_speed,
       last(lat, time) AS last_lat, last(lng, time) AS last_lng
FROM gps_point GROUP BY bucket, device_id
WITH NO DATA;
SELECT add_continuous_aggregate_policy('gps_point_hourly', start_offset => INTERVAL '3 hours', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '30 minutes', if_not_exists => true);
SELECT add_retention_policy('gps_point_hourly', INTERVAL '3 years', if_not_exists => true);   -- a rollup can outlive the raw points
```

**Latest position.** A normal table, one row per device, updated with every write: a live map reads one row per device instead of searching the hypertable.
```sql
CREATE TABLE IF NOT EXISTS gps_point_latest (
  device_id  bigint PRIMARY KEY,
  time       timestamptz NOT NULL,
  location   geography(Point, 4326) NOT NULL,
  speed      real
);
CREATE INDEX IF NOT EXISTS gps_point_latest_location_idx ON gps_point_latest USING gist (location);
```

**Write.** One round trip per batch, in one transaction; a retried batch is ignored by the key.
```sql
INSERT INTO gps_point (time, device_id, lat, lng, speed)
SELECT * FROM unnest($1::timestamptz[], $2::bigint[], $3::float8[], $4::float8[], $5::real[])
ON CONFLICT (device_id, time) DO NOTHING;
INSERT INTO gps_point_latest (device_id, time, location, speed)
VALUES ($1, $2, ST_SetSRID(ST_MakePoint($4, $3), 4326)::geography, $5)    -- MakePoint(lng, lat)
ON CONFLICT (device_id) DO UPDATE SET time = EXCLUDED.time, location = EXCLUDED.location, speed = EXCLUDED.speed
WHERE gps_point_latest.time < EXCLUDED.time;                               -- a late batch never moves a device back
```

**Read.** Always filter on the time column, so only the chunks in range are read.
```sql
SELECT time, lat, lng, speed FROM gps_point WHERE device_id = $1 AND time >= $2 AND time < $3 ORDER BY time;   -- route replay
SELECT device_id, location FROM gps_point_latest WHERE time > now() - INTERVAL '2 minutes';                   -- live map
SELECT device_id FROM gps_point_latest WHERE ST_DWithin(location, $1::geography, 5000)
ORDER BY location <-> $1::geography LIMIT 5;                                                                  -- nearest
SELECT device_id, ST_Length(ST_MakeLine(ST_MakePoint(lng, lat) ORDER BY time)::geography) / 1000 AS km
FROM gps_point WHERE time >= $1 AND time < $2 GROUP BY device_id;                                             -- distance
SELECT bucket, device_id, avg_speed, max_speed FROM gps_point_hourly WHERE bucket >= now() - INTERVAL '30 days';   -- report
SELECT time_bucket_gapfill('5 minutes', time) AS bucket, count(*) AS points FROM gps_point
WHERE device_id = $1 AND time > now() - INTERVAL '1 day' AND time <= now() GROUP BY bucket ORDER BY bucket;  -- signal gaps
```

**Check.**
```sql
SELECT hypertable_name, num_chunks, compression_enabled FROM timescaledb_information.hypertables;
SELECT job_id, proc_name, hypertable_name, schedule_interval FROM timescaledb_information.jobs;   -- policies
SELECT * FROM timescaledb_information.job_stats;                                                 -- last runs, failures
SELECT pg_size_pretty(hypertable_size('gps_point')), * FROM hypertable_compression_stats('gps_point');
```

## Points from a device webhook

Many device clouds push each point to a URL you give them, one HTTP request per point, without a signature and without retrying a failed push. The route takes the point, puts it in Atom's create buffer for the time-series database, and replies at once; the buffer writes many points in one insert.

```python
# .env
config_postgres_url_telematics=postgresql://<user>:<password>@<host>:5432/telematics?sslmode=require
config_postgres_buffer_flush_auto_sec_telematics=2    # write device points every 2 s; master keeps its own interval
config_webhook_token_devices=<long random value>

# config_extend.py: the sender can't log in or sign, so it is checked by IP and a shared token
"/gps/point-push": {"id": 300, "auth": [], "ip_allow": ["203.0.113.0/24"], "token_verify": {"secret": "config_webhook_token_devices"}},

# function_extend/gps.py
async def func_gps_point_push(*, app_state, point: dict) -> str:
    if point.get("lat") is None or point.get("lng") is None: return "skipped"    # nothing to store; still a success for the sender
    row = {"time": datetime.fromtimestamp(point["time_ms"] / 1000, UTC), "device_id": point["device_id"], "lat": point["lat"], "lng": point["lng"], "speed": point.get("speed")}
    return await app_state.func_postgres_create(client_postgres=app_state.client_postgres_dict["telematics"], client_postgres_conn=None, client_password_hasher=None,
        cache_postgres_schema=app_state.cache_postgres_schema_dict["telematics"], buffer_postgres=app_state.buffer_postgres_create,
        buffer_rows_max=app_state.config_buffer_rows_max, buffer_full_mode="reject", column_regex=app_state.func_column_regex(app_state=app_state, table="gps_point", connection="telematics"),
        buffer_limit=app_state.func_buffer_limit(app_state=app_state, table="gps_point", connection="telematics"), mode="buffer", table="gps_point", obj_list=[row],
        connection="telematics", on_conflict="nothing")
```

| Part | Why |
|---|---|
| `connection="telematics"` | Buffered points keep their database and are flushed through its pool ([database.md](database.md#4-in-memory-write-buffering)) |
| `on_conflict="nothing"` | The key `(device_id, time)` skips a point sent twice; a batch never fails on a duplicate |
| No `id` column | Fine: the insert asks for `RETURNING id` only when the table has one |
| `config_postgres_buffer_flush_auto_sec_telematics` | A short interval keeps the points that only live in memory few; a crash loses at most that many seconds |
| `buffer_limit` (`{"gps_point": 1000}` in the schema's `control`) | A busy table is written as soon as that many points wait, before the timer |
| Reply in the sender's format | Many senders treat any other body or a slow reply as a failure and drop the point |
| A backfill job | The sender doesn't retry: a scheduled script reads the sender's history API for the last hours and writes it with the same `on_conflict="nothing"`, so only the gaps are added |

`gps_point_latest` (the live map) is updated by the backfill job or a short scheduled `INSERT … SELECT DISTINCT ON (device_id) … ON CONFLICT (device_id) DO UPDATE` from the newest points, not per push, so the push route stays one buffered append.

## Apache edition (managed services)

Where `SHOW timescaledb.license;` returns `apache` (for example Azure Database for PostgreSQL), the edition can't be changed by a setting.

| Works | Doesn't: use instead |
|---|---|
| Hypertables, chunks, `time_bucket`, `drop_chunks`, `show_chunks`, `set_chunk_time_interval` | Compression: size the disk for raw data, keep only the columns reports need, and a shorter retention |
| Every read sample above except gapfill | `add_retention_policy`: a scheduled script (`script_extend/`, [schedule.md](schedule.md)) running `SELECT drop_chunks('gps_point', older_than => INTERVAL '90 days')` |
| `ON CONFLICT`, PostGIS, indexes | Continuous aggregates: a normal rollup table (`bucket`, `device_id`, totals, primary key on both), refreshed by a scheduled `INSERT … SELECT time_bucket(…) … WHERE time >= now() - INTERVAL '3 hours' GROUP BY … ON CONFLICT (bucket, device_id) DO UPDATE` |
| | `time_bucket_gapfill`: `generate_series` of buckets `LEFT JOIN`ed to the grouped points |

Code written this way also runs on the Community edition; moving there later adds compression and policies without changing the routes.

## What Atom does with these tables

Atom manages the tables in the database's schema: it creates them, adds columns, indexes and checks, and removes the indexes and checks it made that the schema no longer lists. A table not in the schema is never dropped or altered. Triggers go only on the tables that schema lists and follow its `control` (`row_update_disabled`, `row_delete_disabled`, `row_delete_max`: none listed, none added; the switches `is_updated_at_set` and `is_protected_delete_disabled` act only on a table with those columns):

| Key | Effect on a hypertable |
|---|---|
| `control` `"is_truncate_disabled": True` (default) | `TRUNCATE` is refused; retention and `drop_chunks` still work |
| the table in `control.row_delete_max` | its trigger uses a transition table, which hypertables refuse: leave it off a hypertable |

Also:
- With `config_is_postgres_schema_init` off, startup changes nothing and stops when the database differs from its schema, until `script.postgres_schema_plan --apply` runs the changes.
- The schema cache lists the tables after the start (`GET /admin/postgres-schema?connection=telematics`). Admin reads, exports, group-by and distinct work with `?connection=telematics` (reads with `order=time desc`); `/admin/object-create?connection=telematics&table=gps_point` writes points (it sets `created_by_id` only when the table has it), while `/my` and `/public` creates answer 400 `table 'gps_point' lacks required 'created_by_id' column`; update, delete and relation fetch answer 400 `table 'gps_point' has no id`; public and private reads only reach a table in `control.public_read` / `private_read`.
- Login, users and permissions stay on master: the same token reaches `telematics`, and the user checks read master.
- `script.postgres_backup` copies the master database only: back the time-series database up with database tools.
