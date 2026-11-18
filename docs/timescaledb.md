# TimescaleDB

For high-volume time-series data: GPS, IoT sensors, metrics, events. TimescaleDB is a PostgreSQL extension, so Atom connects to it like any Postgres database: no new client, driver or setting. Everything below is general: create as many hypertables, rollups and policies as a feature needs. The examples use a `gps_point` table (one location per device per timestamp).

## Main steps

A guideline, not a fixed recipe: adapt it to the feature. Examples use the connection name `timescale` and the feature `gps`.

1. **Server.** PostgreSQL with the TimescaleDB **Community** edition (the Apache-only build, as on some managed services, has no compression, retention or rollups). `shared_preload_libraries = 'timescaledb'`, then `timescaledb-tune`. Check: `SHOW timescaledb.license;` returns `timescale`.
2. **Extension**, once, by a database admin: `CREATE EXTENSION IF NOT EXISTS timescaledb;` (plus `postgis` for locations).
3. **Connect.** TimescaleDB is plain Postgres, so its URL is a normal Postgres URL: one `.env` line, no code.
   ```
   config_postgres_url_timescale=postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require
   ```
   Atom opens the pool at startup and the app gets it as `app_state.client_postgres_dict["timescale"]`, like any other database ([database.md](database.md)).
4. **Schema file.** Create `files_extend/<feature>_schema.sql` (here `files_extend/gps_schema.sql`) with the tables, hypertables, indexes, policies and rollups, built from the [samples](#samples).
5. **Run it** in that database with any Postgres client, e.g. `psql "<url>" -v ON_ERROR_STOP=1 -f files_extend/gps_schema.sql`. Atom never runs this file and never changes this database's schema; it manages `master` only.
6. **Reload** the schema cache: restart Atom or call `GET /admin/sync`.
7. **APIs.** The feature's own `function_extend/gps.py` (`func_gps_*` with the SQL), `router_extend/gps.py` (reads params, calls one function) and a `config_api` entry per route in `config_extend.py`, as for any feature ([extend.md](extend.md)).
8. **UI.** A page in `static_extend/gps/` that calls those APIs (map, charts, reports), built to [frontend.md](frontend.md); business rules in `docs_extend/gps.md`, tests in `tests_extend/test_gps.py`.

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
    rows = await app_state.func_gps_route_read(client_postgres=app_state.client_postgres_dict["timescale"], device_id=p["device_id"], start=datetime.fromisoformat(p["start"]), end=datetime.fromisoformat(p["end"]))
    return {"status": 1, "message": rows}
```

## Standard practices

| Practice | Why |
|---|---|
| A separate database, `config_postgres_url_<name>`, named for what it holds | Heavy time-series load stays off `master`; the pool can be sized alone (`config_postgres_pool_max_size_<name>`) |
| Schema only in `files_extend/<feature>_schema.sql`, committed, one file per feature | One source of the schema, reviewed with the code; never change the database by hand |
| Every statement safe to run again ([forms below](#safe-to-run-again)) | After a change, run the whole file again; what is already there is skipped |
| Hypertables stay out of `config_postgres["table"]` | Atom's tables have `id` as the only primary key; a hypertable's primary and unique keys must include its time column |
| The feature's own routes and functions | Atom's generic object routes expect `id` and `created_by_id`, which a hypertable doesn't have |
| Compression and retention from the first day | Raw points grow fast; old chunks shrink about 90% and expire without a slow `DELETE` |
| Every read filters on the time column | Only the chunks in range are read |
| Rollups for reports, a `<table>_latest` table for live views | Long ranges and live maps without scanning raw points |
| Batched writes with `ON CONFLICT DO NOTHING` | One round trip per batch; a retried batch is not written twice |

**On `master` instead** (no separate database): skip steps 3 to 5 and put the statements in `config_postgres["sql"]` in `config_extend.py`; Atom runs them at every startup.

## Safe to run again

The schema file is run again after every change, and `config_postgres["sql"]` on `master` runs at every startup, so each statement must do nothing when its object is already there. On `master`, put one statement per list item: `"sql": {**base_config_postgres["sql"], "<feature>": ["<statement 1>", "<statement 2>", …]}`. Each runs on its own, and a continuous aggregate can't be created inside a multi-statement string.

| Object | Safe form |
|---|---|
| Table | `CREATE TABLE IF NOT EXISTS …` |
| New column later | `ALTER TABLE … ADD COLUMN IF NOT EXISTS …` (a `CREATE TABLE IF NOT EXISTS` never adds it) |
| Index | `CREATE INDEX IF NOT EXISTS <name> ON …` (name it) |
| Hypertable | `create_hypertable(…, if_not_exists => true)` |
| Compression settings | inside `DO $$ … IF NOT EXISTS (… compression_enabled) …` (sample below) |
| Policies | `add_compression_policy / add_retention_policy / add_continuous_aggregate_policy(…, if_not_exists => true)` |
| Rollup | `CREATE MATERIALIZED VIEW IF NOT EXISTS … WITH NO DATA` |

`if_not_exists` keeps what is there: a changed interval in the config is not applied. To change a policy or chunk size, run `remove_<kind>_policy(…)` or `set_chunk_time_interval(…)` once by hand, then update the config.

## Samples

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

## What Atom does with these tables (on `master`)

A table Atom doesn't manage (not in `config_postgres["table"]`) is never dropped or altered: column, index and constraint cleanup touches managed tables only. On every public table, managed or not, startup does add:

| What | Effect on a hypertable |
|---|---|
| `trigger_truncate_disable_<table>` (unless `config_postgres["control"]["is_truncate_table"]`) | `TRUNCATE` is refused; retention and `drop_chunks` still work |
| `updated_at` and `is_protected` triggers | only when the table has those columns |
| `"*"` in `table_row_delete_disable` or `table_row_delete_disable_bulk` | adds delete triggers to every table; the bulk one uses a transition table, which hypertables refuse, so name tables instead of `"*"` |

Also:
- With `config_is_postgres_schema_init` off, a new table's triggers count as changes, so startup stops until `script.postgres_schema_plan --apply` adds them.
- The schema cache lists the table after a restart or `GET /admin/sync`; admin routes (role 1) can read and write it; `/my/object-create` refuses it (no `created_by_id`); public and private reads only reach tables listed in `config_table_public_read_allowed` / `config_table_private_read_allowed`.
- `script.postgres_backup` copies every public table to CSV: with large hypertables, leave it off or back the database up with database tools.
