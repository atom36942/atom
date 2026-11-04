# import
import os
import platform
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from importlib import metadata
from typing import Any
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
    """Pool use of every PostgreSQL connection (which one log_api writes to), and for one database: where it is (database, host, port, user), size, cache hit ratio, connections, long-running queries, waiting locks and the biggest tables."""
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
    slow_queries = await app_state.func_postgres_slow_queries_read(client_postgres=client_postgres, limit=top, order="total_time")
    return {"connection": connection, "pools": pools, "is_enabled": True, "info": info, "states": [dict(row) for row in states], "long_queries": [dict(row) for row in queries], "tables": [dict(row) for row in tables], "slow_queries": slow_queries}

async def func_monitor_queues(*, client_redis: Any, channels: list) -> dict:
    """Redis queue backlog per channel: jobs waiting (<channel>), running (<channel>_processing) and kept after their last retry (<channel>_failed), and whether a consumer holds the channel. Channels: Atom's, plus any a consumer has used (found by their key names). Counts only, never payloads."""
    if not client_redis: return {"is_enabled": False, "channels": []}
    found = {key.decode().rsplit("_", 1)[0] for pattern in ("*_processing", "*_failed", "*_consumer") async for key in client_redis.scan_iter(match=pattern, count=500)}
    names = sorted(set(channels) | found)
    async with client_redis.pipeline(transaction=False) as pipe:
        for name in names: pipe.llen(name).llen(f"{name}_processing").llen(f"{name}_failed").exists(f"{name}_consumer")
        counts = await pipe.execute()
    return {"is_enabled": True, "channels": [{"channel": name, "waiting": counts[i * 4], "running": counts[i * 4 + 1], "failed": counts[i * 4 + 2], "is_consumer": bool(counts[i * 4 + 3])} for i, name in enumerate(names)]}

def func_monitor_background(*, app_state: State) -> dict:
    """Work this worker does outside requests: periodic tasks, rows waiting in the write buffers, running background tasks, open websockets and error counters."""
    task_names = {"runtime_task_postgres_buffer_flush": "Buffer flush", "runtime_task_inmemory_cache_cleanup": "In-memory cache cleanup", "runtime_task_otp_cleanup": "OTP cleanup", "runtime_task_log_api_cleanup": "log_api cleanup", "runtime_task_memory_history": "RAM history"}
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
        "server": {"python": platform.python_version(), "platform": platform.platform(terse=True), "pid": os.getpid(), "workers": state.get("config_uvicorn_workers", 1), "is_prod": state.get("config_is_prod"), "is_read_only": state.get("config_is_read_only"), "atom_version": state.get("cache_atom_version"),
                   "routes": len(app_routes), "routes_project": project_routes, "apis_configured": len(state.get("config_api", {})), "functions": len(functions), "functions_project": project_functions},
        "packages": versions,
        "clients": clients,
        "config": [{"name": name, "value": func_monitor_config_value(name=name, value=state[name])} for name in sorted(state) if name.startswith("config_")],
    }

async def func_monitor_report(*, app_state: State, view: str, hours: int = 24, connection: str = "master", app_routes: list = None) -> dict:
    """One monitor view: memory, requests, errors, database, background or app."""
    if view == "memory": return await app_state.func_memory_report(app_state=app_state)
    if view == "requests": return await func_monitor_requests(client_postgres=getattr(app_state, "client_postgres_log_api", None), hours=hours)
    if view == "errors": return await func_monitor_errors(client_postgres=getattr(app_state, "client_postgres_log_api", None), hours=hours)
    if view == "database": return await func_monitor_database(app_state=app_state, connection=connection)
    if view == "background": return {**func_monitor_background(app_state=app_state), "queues": await func_monitor_queues(client_redis=app_state.client_redis_dict.get("queue"), channels=list(app_state.func_consumer_channels()))}
    if view == "app": return func_monitor_app(app_state=app_state, app_routes=app_routes or [])
    raise Exception(f"invalid view: {view}")
