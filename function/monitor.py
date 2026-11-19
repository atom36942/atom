# import
import asyncio
import os
import platform
import time
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from importlib import metadata
from typing import Any
from urllib.parse import urlsplit
import asyncpg
import orjson
from starlette.datastructures import State

# function
async def func_monitor_requests(*, client_postgres: asyncpg.Pool | None, hours: int, top: int = 20, timeout_sec: int = 15) -> dict:
    """Traffic from log_api over the last hours: totals, a timeline, the busiest and slowest paths, status codes and the most active users."""
    if not client_postgres: return {"is_enabled": False}
    since, unit = datetime.now(UTC) - timedelta(hours=hours), "minute" if hours <= 1 else "hour"
    async with client_postgres.acquire() as conn:
        totals = dict(await conn.fetchrow("""
            SELECT count(*) AS requests, count(*) FILTER (WHERE status_code >= 500) AS errors_5xx, count(*) FILTER (WHERE status_code BETWEEN 400 AND 499) AS errors_4xx,
                   count(DISTINCT created_by_id) AS users, round(avg(response_time_ms))::int AS avg_ms, round(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms))::int AS p95_ms
            FROM log_api WHERE created_at >= $1""", since, timeout=timeout_sec))
        timeline = await conn.fetch(f"""
            SELECT date_trunc('{unit}', created_at AT TIME ZONE 'UTC') AS bucket, count(*) AS requests, count(*) FILTER (WHERE status_code >= 400) AS errors, round(avg(response_time_ms))::int AS avg_ms
            FROM log_api WHERE created_at >= $1 GROUP BY 1 ORDER BY 1""", since, timeout=timeout_sec)    # noqa: S608 (unit is one of two literals)
        paths = await conn.fetch("""
            SELECT method, path, count(*) AS requests, count(*) FILTER (WHERE status_code >= 400) AS errors, round(avg(response_time_ms))::int AS avg_ms,
                   round(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms))::int AS p95_ms, max(response_time_ms) AS max_ms
            FROM log_api WHERE created_at >= $1 GROUP BY method, path ORDER BY requests DESC LIMIT $2""", since, top, timeout=timeout_sec)
        slowest = await conn.fetch("""
            SELECT method, path, count(*) AS requests, round(avg(response_time_ms))::int AS avg_ms, round(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms))::int AS p95_ms, max(response_time_ms) AS max_ms
            FROM log_api WHERE created_at >= $1 GROUP BY method, path ORDER BY p95_ms DESC NULLS LAST LIMIT $2""", since, top, timeout=timeout_sec)
        statuses = await conn.fetch("SELECT status_code, count(*) AS requests FROM log_api WHERE created_at >= $1 GROUP BY 1 ORDER BY 2 DESC", since, timeout=timeout_sec)
        users = await conn.fetch("""
            SELECT created_by_id AS user_id, count(*) AS requests, count(*) FILTER (WHERE status_code >= 400) AS errors, max(created_at) AS last_at
            FROM log_api WHERE created_at >= $1 AND created_by_id IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT $2""", since, top, timeout=timeout_sec)
    # every bucket in the window (UTC, whatever the database time zone), so quiet minutes or hours show as zero
    step = timedelta(minutes=1) if unit == "minute" else timedelta(hours=1)
    by_bucket, bucket, end, filled = {row["bucket"].replace(tzinfo=UTC): {**dict(row), "bucket": row["bucket"].replace(tzinfo=UTC)} for row in timeline}, since.replace(second=0, microsecond=0, **({} if unit == "minute" else {"minute": 0})), datetime.now(UTC), []
    while bucket <= end:
        filled.append(by_bucket.get(bucket) or {"bucket": bucket, "requests": 0, "errors": 0, "avg_ms": None})
        bucket += step
    return {"is_enabled": True, "hours": hours, "unit": unit, "totals": totals, "timeline": filled, "paths": [dict(row) for row in paths], "slowest": [dict(row) for row in slowest], "statuses": [dict(row) for row in statuses], "users": [dict(row) for row in users]}

async def func_monitor_errors(*, client_postgres: asyncpg.Pool | None, hours: int, top: int = 20, latest: int = 50, timeout_sec: int = 15) -> dict:
    """Failed requests from log_api over the last hours: by path and status, and the latest ones. Background failures are in the background view."""
    if not client_postgres: return {"is_enabled": False}
    since = datetime.now(UTC) - timedelta(hours=hours)
    async with client_postgres.acquire() as conn:
        groups = await conn.fetch("""
            SELECT method, path, status_code, count(*) AS requests, max(created_at) AS last_at, (array_agg(error ORDER BY created_at DESC) FILTER (WHERE error IS NOT NULL))[1] AS last_error
            FROM log_api WHERE created_at >= $1 AND status_code >= 400 GROUP BY 1, 2, 3 ORDER BY requests DESC LIMIT $2""", since, top, timeout=timeout_sec)
        rows = await conn.fetch("""
            SELECT created_at, method, path, status_code, created_by_id AS user_id, response_time_ms, left(error, 500) AS error
            FROM log_api WHERE created_at >= $1 AND status_code >= 400 ORDER BY created_at DESC LIMIT $2""", since, latest, timeout=timeout_sec)
    return {"is_enabled": True, "hours": hours, "groups": [{**dict(row), "last_error": (row["last_error"] or "")[:500]} for row in groups], "latest": [dict(row) for row in rows]}

async def func_monitor_database(*, app_state: State, connection: str, top: int = 20, long_query_sec: int = 5, timeout_sec: int = 15) -> dict:
    """Pool use of every PostgreSQL connection (which one log_api writes to), and for one database: where it is (database, host, port, user), size, cache hit ratio, connections, long-running queries, waiting locks,
    the biggest tables, and whether the server needs upgrading (func_monitor_database_upgrade)."""
    client_postgres_dict = getattr(app_state, "client_postgres_dict", {})
    log_database = getattr(app_state, "config_postgres_db_log_api", None) if getattr(app_state, "config_is_log_api", True) else None
    pools = [{"name": name, "size": pool.get_size(), "idle": pool.get_idle_size(), "min": pool.get_min_size(), "max": pool.get_max_size(), "is_log_api": name == log_database} for name, pool in client_postgres_dict.items()]
    client_postgres = client_postgres_dict.get(connection)
    if not client_postgres: return {"connection": connection, "pools": pools, "is_enabled": False}
    async with client_postgres.acquire() as conn:
        info = dict(await conn.fetchrow("""
            SELECT current_database() AS name, current_user AS user_name, host(inet_server_addr()) AS host, inet_server_port() AS port, current_setting('server_version') AS version, pg_database_size(current_database()) AS size_bytes, current_setting('max_connections')::int AS max_connections,
                   (SELECT round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2)::float FROM pg_stat_database WHERE datname = current_database()) AS cache_hit_percent,
                   (SELECT count(*) FROM pg_stat_activity) AS connections, (SELECT count(*) FROM pg_locks WHERE NOT granted) AS locks_waiting""", timeout=timeout_sec))
        states = await conn.fetch("SELECT coalesce(state, 'background') AS state, count(*) AS connections FROM pg_stat_activity WHERE datname = current_database() GROUP BY 1 ORDER BY 2 DESC", timeout=timeout_sec)
        queries = await conn.fetch("""
            SELECT pid, usename AS user_name, state, wait_event_type, extract(epoch FROM now() - query_start)::int AS running_sec, left(query, 500) AS query
            FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state <> 'idle' AND query_start < now() - make_interval(secs => $1)
            ORDER BY query_start LIMIT $2""", long_query_sec, top, timeout=timeout_sec)
        tables = await conn.fetch("""
            SELECT schemaname || '.' || relname AS name, n_live_tup AS rows, n_dead_tup AS dead_rows, pg_total_relation_size(relid) AS size_bytes, seq_scan, idx_scan,
                   greatest(last_vacuum, last_autovacuum) AS vacuumed_at, greatest(last_analyze, last_autoanalyze) AS analyzed_at
            FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT $1""", top, timeout=timeout_sec)
        # the counters behind the upgrade check, all since their last reset: reads, spills to disk and deadlocks of this database; the net bytes its tables gained
        # (rows inserted minus deleted, times each table's bytes per row); the data of every database on the server this login may open; the WAL written (pg_stat_wal, PostgreSQL 14 and later)
        stats = dict(await conn.fetchrow("""
            SELECT blks_hit, blks_read, temp_bytes, deadlocks, coalesce(stats_reset, pg_postmaster_start_time()) AS stats_reset, extract(epoch FROM now() - coalesce(stats_reset, pg_postmaster_start_time()))::float AS stats_age_sec,
                   pg_size_bytes(current_setting('shared_buffers')) AS shared_buffers_bytes, pg_size_bytes(current_setting('work_mem')) AS work_mem_bytes, current_setting('server_version_num')::int AS version_num,
                   (SELECT sum((n_tup_ins - n_tup_del) * pg_total_relation_size(relid)::float / greatest(n_live_tup, 1)) FROM pg_stat_user_tables) AS net_bytes,
                   (SELECT sum(pg_database_size(datname)) FROM pg_database WHERE datallowconn AND has_database_privilege(datname, 'CONNECT'))::bigint AS server_bytes
            FROM pg_stat_database WHERE datname = current_database()""", timeout=timeout_sec))
        wal = dict(await conn.fetchrow("""
            SELECT wal_bytes::float, extract(epoch FROM now() - coalesce(stats_reset, pg_postmaster_start_time()))::float AS age_sec, pg_size_bytes(current_setting('max_wal_size')) AS max_wal_bytes,
                   extract(epoch FROM current_setting('checkpoint_timeout')::interval)::float AS checkpoint_timeout_sec FROM pg_stat_wal""", timeout=timeout_sec)) if stats["version_num"] >= 140000 else {}
    slow_queries = await app_state.func_postgres_slow_queries_read(client_postgres=client_postgres, limit=top, order="total_time")
    upgrade = func_monitor_database_upgrade(info=info, stats=stats, wal=wal)
    return {"connection": connection, "pools": pools, "is_enabled": True, "info": info, "states": [dict(row) for row in states], "long_queries": [dict(row) for row in queries], "tables": [dict(row) for row in tables], "slow_queries": slow_queries, "upgrade": upgrade}

def func_monitor_database_upgrade(*, info: dict, stats: dict, wal: dict) -> dict:
    """Whether the PostgreSQL server needs upgrading, from its own counters: one signal per resource (status ok, watch, upgrade or unknown; its value and what it means), the actions to ask DevOps for,
    and that request as text to copy. wal: pg_stat_wal's bytes and age with max_wal_size and checkpoint_timeout (empty before PostgreSQL 14). Counters run since their last reset, so a young window (under a day) is said to be too short to judge. Deadlocks are a code issue: they never ask for an upgrade."""
    def size(n: float) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(n) < 1024 or unit == "TB": return f"{n:.0f} {unit}" if unit in ("B", "KB") or abs(n) >= 10 else f"{n:.1f} {unit}"
            n /= 1024
    def level(value: float | None, watch: float, upgrade: float, below: bool = False) -> str:
        if value is None: return "ok"
        if below: return "upgrade" if value < upgrade else "watch" if value < watch else "ok"
        return "upgrade" if value >= upgrade else "watch" if value >= watch else "ok"
    days = max((stats.get("stats_age_sec") or 0) / 86400, 1 / 24)
    signals, actions = [], []
    # data size: every database on the server and its growth since the counters reset, for information (the disk size is not visible to PostgreSQL)
    used, growth = stats.get("server_bytes") or info.get("size_bytes") or 0, max((stats.get("net_bytes") or 0) / days, 0)
    grows = f"+{size(growth * 30)} a month" if growth >= 1024 ** 2 / 30 else "not growing"
    signals.append({"name": "Data size", "status": "unknown", "value": size(used), "detail": grows})
    # connections: every app's, against the server's limit
    connections_pct = info["connections"] / info["max_connections"] * 100 if info.get("max_connections") else None
    status = level(connections_pct, 60, 80)
    signals.append({"name": "Connections", "status": status, "value": f"{info.get('connections')} of {info.get('max_connections')}", "detail": "all apps, vs max_connections"})
    if status == "upgrade": actions.append(f"More connections: a bigger tier or PgBouncer ({info.get('connections')} of {info.get('max_connections')} used)")
    # memory: reads served from RAM; judged only once there are enough reads
    reads = (stats.get("blks_hit") or 0) + (stats.get("blks_read") or 0)
    hit = stats["blks_hit"] / reads * 100 if reads >= 10000 else None
    status = level(hit, 99, 95, below=True)
    signals.append({"name": "Memory", "status": status, "value": "—" if hit is None else f"{hit:.1f}%", "detail": "too few reads yet" if hit is None else f"reads from RAM, aim 99%; shared_buffers {size(stats.get('shared_buffers_bytes') or 0)}"})
    if status == "upgrade": actions.append(f"More RAM: a bigger tier ({hit:.1f}% of reads from memory)")
    # sorts and joins too big for work_mem spill to temporary files
    spill = (stats.get("temp_bytes") or 0) / days
    status = level(spill, 512 * 1024 ** 2, 5 * 1024 ** 3)
    signals.append({"name": "Work memory", "status": status, "value": f"{size(spill)} a day", "detail": f"spilled to disk; work_mem {size(stats.get('work_mem_bytes') or 0)}"})
    if status == "upgrade": actions.append(f"Raise work_mem from {size(stats.get('work_mem_bytes') or 0)}, with RAM to spare ({size(spill)} a day spilled to disk)")
    # write load: the WAL written in one checkpoint interval against max_wal_size; at 100% writes force checkpoints before their time. Not the requested-checkpoint count:
    # backups and manual CHECKPOINTs request them too (on Azure most of them), whatever the write load
    per_interval = wal["wal_bytes"] / wal["age_sec"] * wal["checkpoint_timeout_sec"] if wal.get("age_sec") and wal.get("checkpoint_timeout_sec") and wal.get("wal_bytes") is not None else None
    load = per_interval / wal["max_wal_bytes"] * 100 if per_interval is not None and wal.get("max_wal_bytes") else None
    status = level(load, 50, 100)
    signals.append({"name": "Write load", "status": status, "value": "—" if load is None else f"{load:.0f}% of max_wal_size", "detail": "needs PostgreSQL 14+" if load is None else f"{size(per_interval)} WAL per checkpoint interval"})
    if status == "upgrade": actions.append(f"Raise max_wal_size from {size(wal['max_wal_bytes'])}, or more IOPS ({size(per_interval)} WAL per checkpoint interval)")
    # deadlocks: transactions locking the same rows in different orders, fixed in the code
    deadlocks = stats.get("deadlocks") or 0
    signals.append({"name": "Deadlocks", "status": "watch" if deadlocks else "ok", "value": f"{deadlocks}", "detail": "a code issue, not an upgrade" if deadlocks else ""})
    statuses = {signal["status"] for signal in signals}
    verdict = "upgrade" if "upgrade" in statuses else "watch" if "watch" in statuses else "ok"
    since = stats.get("stats_reset")
    window = f"counters since {since:%Y-%m-%d}" if since else "counters of unknown age"
    if (stats.get("stats_age_sec") or 0) < 86400: window += " (under a day: judge again after a few days)"
    where = f"{info.get('name')} on {info.get('host') or 'a local socket'}"
    request = (f"PostgreSQL server for database {where} needs an upgrade (from Atom Monitor, {window}):\n" + "\n".join(f"- {action}" for action in actions)) if actions else ""
    return {"verdict": verdict, "signals": signals, "actions": actions, "request": request, "window": window}

async def func_monitor_queues(*, client_redis: Any, channels: list) -> dict:
    """Redis queue backlog per channel: jobs waiting (<channel>), running (<channel>_processing) and kept after their last retry (<channel>_failed), and whether a consumer holds the channel. Channels: Atom's, plus any a consumer has used (found by their key names). Counts only, never payloads."""
    if not client_redis: return {"is_enabled": False, "channels": []}
    found = {key.decode().rsplit("_", 1)[0] for pattern in ("*_processing", "*_failed", "*_consumer") async for key in client_redis.scan_iter(match=pattern, count=500)}
    names = sorted(set(channels) | found)
    async with client_redis.pipeline(transaction=False) as pipe:
        for name in names: pipe.llen(name).llen(f"{name}_processing").llen(f"{name}_failed").exists(f"{name}_consumer")
        counts = await pipe.execute()
    return {"is_enabled": True, "channels": [{"channel": name, "waiting": counts[i * 4], "running": counts[i * 4 + 1], "failed": counts[i * 4 + 2], "is_consumer": bool(counts[i * 4 + 3])} for i, name in enumerate(names)]}

async def func_monitor_redis(*, client_redis_dict: dict, url_dict: dict, timeout_sec: float = 5) -> dict:
    """Every Redis connection (config_redis_url_<name>), read-only: where it is (host, port, db; never the password), memory used and its limit (None when the provider hides it, as Azure does), keys, hit ratio, load, evictions and one timed PING from this server. One that cannot be reached shows its error."""
    async def one(name: str, client: Any) -> dict:
        try: parts = urlsplit(url_dict.get(name) or "")
        except ValueError: parts = urlsplit("")
        row = {"name": name, "key_prefix": getattr(client, "atom_key_prefix", ""), "host": parts.hostname or "", "port": parts.port, "db": parts.path.strip("/") or "0", "is_tls": parts.scheme == "rediss"}
        if client is None: return {**row, "status": "off", "error": "no client"}
        try:
            async def read() -> tuple:
                await client.ping()    # opens a connection if the pool has none, so the timed one is the round trip alone
                start = time.perf_counter()
                await client.ping()
                ping_ms = round((time.perf_counter() - start) * 1000, 1)
                return ping_ms, await client.info(), await client.dbsize()
            ping_ms, info, keys = await asyncio.wait_for(read(), timeout=timeout_sec)
        except Exception as error: return {**row, "status": "error", "error": str(error)[:300] or type(error).__name__}
        hits, misses, limit = info.get("keyspace_hits", 0), info.get("keyspace_misses", 0), info.get("maxmemory")
        return {**row, "status": "ok", "error": "", "ping_ms": ping_ms, "version": info.get("redis_version"), "mode": info.get("redis_mode"), "uptime_sec": info.get("uptime_in_seconds"),
                "used_memory_bytes": info.get("used_memory"), "peak_memory_bytes": info.get("used_memory_peak"), "max_memory_bytes": limit or None, "policy": info.get("maxmemory_policy"), "fragmentation": info.get("mem_fragmentation_ratio"),
                "keys": keys, "hits": hits, "misses": misses, "hit_ratio_pct": round(hits / (hits + misses) * 100, 1) if hits + misses else None, "ops_per_sec": info.get("instantaneous_ops_per_sec"),
                "clients": info.get("connected_clients"), "max_clients": info.get("maxclients"), "rejected_connections": info.get("rejected_connections"), "evicted_keys": info.get("evicted_keys"), "expired_keys": info.get("expired_keys")}
    names = sorted({name for name, client in (client_redis_dict or {}).items() if client} | {name for name, url in (url_dict or {}).items() if url})
    return {"connections": list(await asyncio.gather(*(one(name, (client_redis_dict or {}).get(name)) for name in names)))}

def func_monitor_background(*, app_state: State) -> dict:
    """Work this worker does outside requests: periodic tasks, rows waiting in the write buffers, running background tasks, open websockets and error counters."""
    task_names = {"runtime_task_postgres_buffer_flush": "Buffer flush", "runtime_task_inmemory_cache_cleanup": "In-memory cache cleanup", "runtime_task_schedule": "Schedule", "runtime_task_memory_history": "RAM history"}
    tasks = []
    for name, label in task_names.items():
        task = getattr(app_state, name, None)
        status = "off" if task is None else "running" if not task.done() else "cancelled" if task.cancelled() else "failed" if task.exception() else "finished"
        tasks.append({"name": label, "status": status})
    buffers = [{"buffer": buffer, "table": table, "rows": len(rows)} for buffer, cache in (("create", getattr(app_state, "buffer_postgres_create", {})), ("log_api", getattr(app_state, "buffer_postgres_log_api", {}))) for table, rows in list(cache.items())]
    sockets = getattr(app_state, "runtime_message_socket", {})
    return {
        "tasks": tasks,
        "buffers": sorted(buffers, key=lambda item: item["rows"], reverse=True),
        "buffer_rows_max": getattr(app_state, "config_buffer_rows_max", None),
        "background_tasks_running": len(getattr(app_state, "runtime_background_tasks", set())),
        "websockets": sum(len(value) if isinstance(value, (dict, list, set)) else 1 for value in list(sockets.values())),
        "errors": [{"name": name, "count": count} for name, count in sorted(getattr(app_state, "runtime_error_count", {}).items())],
    }

def func_monitor_config_value(*, name: str, value) -> object:
    """A setting as the monitor shows it: secrets and connection URLs only say whether they are set, long lists and dicts show their size."""
    if any(word in name for word in ("password", "secret", "key", "token", "dsn", "url", "connection_string")) and not isinstance(value, bool):
        return "set" if value else "not set"
    if isinstance(value, (dict, list, tuple, set)): return value if len(orjson.dumps(value, default=str, option=orjson.OPT_NON_STR_KEYS)) <= 200 else f"{len(value)} items"
    return value if value is None or isinstance(value, (bool, int, float)) else str(value)[:200]

def func_monitor_database_name(*, url: str | None) -> str:
    """The master database as host[:port] / database, never the user or password, for the line under the page name (a click shows the URL, password hidden): "" when unset or unreadable."""
    try: parts = urlsplit(url or "")
    except ValueError: return ""
    if not parts.hostname: return ""
    port, name = (f":{parts.port}" if parts.port and parts.port != 5432 else ""), parts.path.strip("/")
    return parts.hostname + port + (f" / {name}" if name else "")

def func_monitor_app(*, app_state: State, app_routes: list, packages: tuple = ("fastapi", "starlette", "uvicorn", "asyncpg", "pydantic", "orjson", "redis", "psutil")) -> dict:
    """What this server runs: Atom's version, Python and packages, mode flags, routes and func_* functions (split into Atom's and the project's), which clients are connected, and every setting (secrets masked)."""
    state = vars(app_state)["_state"]
    versions = []
    for name in packages:
        try: versions.append({"name": name, "version": metadata.version(name)})
        except metadata.PackageNotFoundError: continue
    functions = [value for name, value in state.items() if name.startswith("func_") and callable(value)]
    project_functions = sum(1 for value in functions if str(getattr(value, "__module__", "")).startswith("function_extend"))
    project_routes = sum(1 for route in app_routes if str(getattr(getattr(route, "endpoint", None), "__module__", "")).startswith("router_extend"))
    clients = []
    for name, value in sorted(state.items()):
        if not name.startswith("client_"): continue
        is_on = bool(value) if isinstance(value, dict) else value is not None
        clients.append({"name": name, "is_on": is_on, "detail": ", ".join(sorted(value)) if isinstance(value, dict) else ""})
    return {
        "server": {"python": platform.python_version(), "platform": platform.platform(terse=True), "pid": os.getpid(), "workers": state.get("config_uvicorn_workers", 1), "is_prod": state.get("config_is_prod"), "is_read_only": state.get("config_is_read_only"), "atom_version": state.get("cache_atom_version"), "database": func_monitor_database_name(url=(master := state.get("config_postgres_url_master") or (state.get("config_postgres_url_dict") or {}).get("master"))), "database_url": state["func_pgweb_dsn_safe"](master) if master else "",
                   "routes": len(app_routes), "routes_project": project_routes, "apis_configured": len(state.get("config_api", {})), "functions": len(functions), "functions_project": project_functions},
        "packages": versions,
        "clients": clients,
        "config": [{"name": name, "value": func_monitor_config_value(name=name, value=state[name])} for name in sorted(state) if name.startswith("config_")],
    }

async def func_monitor_report(*, app_state: State, view: str, hours: int = 24, connection: str = "master", app_routes: list = None) -> dict:
    """One monitor view: memory, requests, errors, database, background, redis or app; every one also names the master database for the page's header: master_database (host / database) and master_database_url (the URL, password hidden)."""
    if view == "memory": report = await app_state.func_memory_report(app_state=app_state)
    elif view == "requests": report = await func_monitor_requests(client_postgres=getattr(app_state, "client_postgres_log_api", None), hours=hours)
    elif view == "errors": report = await func_monitor_errors(client_postgres=getattr(app_state, "client_postgres_log_api", None), hours=hours)
    elif view == "database": report = await func_monitor_database(app_state=app_state, connection=connection)
    elif view == "background": report = {**func_monitor_background(app_state=app_state), "queues": await func_monitor_queues(client_redis=app_state.client_redis_dict.get("queue"), channels=list(app_state.func_consumer_channels()))}
    elif view == "redis": report = await func_monitor_redis(client_redis_dict=getattr(app_state, "client_redis_dict", None) or {}, url_dict=getattr(app_state, "config_redis_url_dict", None) or {})
    elif view == "app": report = func_monitor_app(app_state=app_state, app_routes=app_routes or [])
    else: raise Exception(f"invalid view: {view}")
    master = getattr(app_state, "config_postgres_url_master", None) or (getattr(app_state, "config_postgres_url_dict", None) or {}).get("master")
    return {**report, "master_database": func_monitor_database_name(url=master), "master_database_url": app_state.func_pgweb_dsn_safe(master) if master else ""}    # the URL with its password hidden (as PgWeb shows it), for the role 1 page
