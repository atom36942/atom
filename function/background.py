"""Atom background functions."""

import asyncio
import time
from typing import Any
import asyncpg
from starlette.datastructures import State

async def func_postgres_buffer_flush_all(*, app_state: State, client_postgres: asyncpg.Pool | None = None, cache_postgres_buffer_create: dict = None, client_postgres_log_api: Any = None, cache_postgres_buffer_log_api: dict = None) -> None:
    """Flush all PostgreSQL create buffers through their respective client pools."""
    if client_postgres and cache_postgres_buffer_create:
        try:
            async with app_state.postgres_buffer_flush_lock:
                await app_state.func_postgres_create(client_postgres=client_postgres, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=cache_postgres_buffer_create, config_column_regex=None, buffer_limit=None, mode="flush", table=None, obj_list=None)
        except Exception as e: print(f"❌ primary buffer flush error: {e}")
    if client_postgres_log_api and cache_postgres_buffer_log_api:
        try:
            async with app_state.postgres_buffer_flush_lock:
                await app_state.func_postgres_create(client_postgres=client_postgres_log_api, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=cache_postgres_buffer_log_api, config_column_regex=None, buffer_limit=None, mode="flush", table=None, obj_list=None)
        except Exception as e: print(f"❌ log api buffer flush error: {e}")

async def func_postgres_buffer_flush_periodic_task(*, app_state: State, client_postgres: asyncpg.Pool | None, cache_postgres_buffer_create: dict, client_postgres_log_api: Any, cache_postgres_buffer_log_api: dict, interval_sec: int = 60) -> None:
    """Periodically flush all PostgreSQL buffers in a background task loop."""
    while True:
        try:
            await asyncio.sleep(interval_sec)
            await app_state.func_postgres_buffer_flush_all(app_state=app_state, client_postgres=client_postgres, cache_postgres_buffer_create=cache_postgres_buffer_create, client_postgres_log_api=client_postgres_log_api, cache_postgres_buffer_log_api=cache_postgres_buffer_log_api)
        except asyncio.CancelledError: break
        except Exception as e: print(f"❌ periodic postgres buffer flush task error: {e}")
    return None

async def func_inmemory_cache_cleanup_periodic_task(*, cache_api_response: dict, cache_ratelimiter: dict, interval_sec: int = 300) -> None:
    """Periodically purges expired items from in-memory cache and ratelimiter dictionaries in a background task loop."""
    while True:
        try:
            await asyncio.sleep(interval_sec)
            now = time.time()
            expired_api_keys = [k for k, v in cache_api_response.items() if isinstance(v, dict) and v.get("expire_at", 0) <= now]
            for k in expired_api_keys: cache_api_response.pop(k, None)
            expired_rl_keys = [k for k, v in cache_ratelimiter.items() if isinstance(v, dict) and v.get("expire_at", 0) <= now]
            for k in expired_rl_keys: cache_ratelimiter.pop(k, None)
        except asyncio.CancelledError: break
        except Exception as e: print(f"❌ in-memory cache cleanup task error: {e}")
    return None

async def func_otp_cleanup(*, conn: asyncpg.Connection, cutoff, timeout_sec: float) -> int:
    """Delete at most 5,000 old OTP rows; leave current codes untouched."""
    result = await conn.execute("DELETE FROM otp WHERE id IN (SELECT id FROM otp WHERE created_at < $1 ORDER BY created_at LIMIT 5000 FOR UPDATE SKIP LOCKED)", cutoff, timeout=timeout_sec)
    return int(result.split()[-1])

async def func_log_api_cleanup(*, conn: asyncpg.Connection, cutoff, timeout_sec: float) -> int:
    """Delete at most 5,000 old API logs from the supplied logging database."""
    result = await conn.execute("DELETE FROM log_api WHERE id IN (SELECT id FROM log_api WHERE created_at < $1 ORDER BY created_at LIMIT 5000 FOR UPDATE SKIP LOCKED)", cutoff, timeout=timeout_sec)
    return int(result.split()[-1])

async def func_cleanup_periodic_task(*, client_postgres: asyncpg.Pool, retention_day: int | None, cleanup, lock_id: int) -> None:
    """Run a fixed-table cleanup hourly, with a 30-second budget per run."""
    if retention_day is None or client_postgres is None: return
    while True:
        try:
            await asyncio.sleep(3600)
            async with client_postgres.acquire(timeout=5) as conn:
                # Stable session locks coordinate all app workers on this database.
                locked = await conn.fetchval("SELECT pg_try_advisory_lock(1096044365, $1)", lock_id, timeout=5)
                if not locked: continue
                try:
                    cutoff = await conn.fetchval("SELECT CURRENT_TIMESTAMP - ($1::integer * INTERVAL '1 day')", retention_day, timeout=5)
                    deadline = time.monotonic() + 30
                    while (remaining := deadline - time.monotonic()) > 0:
                        deleted = await cleanup(conn=conn, cutoff=cutoff, timeout_sec=min(5, remaining))
                        if deleted < 5000: break
                        await asyncio.sleep(0.1)
                finally:
                    await conn.execute("SELECT pg_advisory_unlock(1096044365, $1)", lock_id, timeout=5)
        except asyncio.CancelledError: break
        except Exception as e: print(f"❌ {cleanup.__name__} periodic cleanup error: {e}")

async def func_async_tasks_cancel(*, task_list: list, timeout_sec: int = 5) -> None:
    """Cancel asynchronous tasks and wait up to the configured timeout for them to finish."""
    task_list = [task for task in task_list if task]
    for task in task_list: task.cancel()
    if task_list: await asyncio.wait(task_list, timeout=timeout_sec)
    return None

async def func_app_tasks_stop(*, app_state: State, timeout_sec: int = 5) -> None:
    """Cancel all runtime background tasks and periodic system tasks on app_state."""
    runtime_tasks = list(getattr(app_state, "runtime_background_tasks", set()))
    periodic_tasks = [getattr(app_state, "postgres_buffer_flush_task", None), getattr(app_state, "inmemory_cache_cleanup_task", None), getattr(app_state, "otp_cleanup_task", None), getattr(app_state, "log_api_cleanup_task", None)]
    await app_state.func_async_tasks_cancel(task_list=runtime_tasks + periodic_tasks, timeout_sec=timeout_sec)
