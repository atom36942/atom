# import
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any
import asyncpg
from starlette.datastructures import State

# function
def func_background_run(*, app_state: State, coroutine: Any) -> None:
    """Run a coroutine without blocking the response; tracked so shutdown waits for it, failures counted under background_task."""
    async def run():
        try: await coroutine
        except asyncio.CancelledError: raise
        except Exception as e: func_runtime_error_record(runtime_error_count=app_state.runtime_error_count, key="background_task", error=e)
    task = asyncio.create_task(run())
    app_state.runtime_background_tasks.add(task)
    task.add_done_callback(app_state.runtime_background_tasks.discard)
    return

def func_runtime_error_record(*, runtime_error_count: dict, key: str, error: Exception, print_every: int = 1) -> None:
    """Count a background failure (shown on the monitor's Background tab, /admin/monitor?view=background) and print it; print_every > 1 thins out per-request errors."""
    runtime_error_count[key] = runtime_error_count.get(key, 0) + 1
    if runtime_error_count[key] == 1 or runtime_error_count[key] % print_every == 0: print(f"❌ {key} error #{runtime_error_count[key]}: {error!r}")
    return

async def func_postgres_buffer_flush_all(*, app_state: State, client_postgres: asyncpg.Pool | None = None, buffer_postgres_create: dict = None, client_postgres_log_api: Any = None, buffer_postgres_log_api: dict = None) -> None:
    """Flush all PostgreSQL create buffers through their respective client pools."""
    if client_postgres and buffer_postgres_create:
        try:
            async with app_state.runtime_lock_postgres_buffer_flush:
                await app_state.func_postgres_create(client_postgres=client_postgres, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=app_state.cache_postgres_schema_dict.get("master", {}), buffer_postgres=buffer_postgres_create, config_column_regex=None, buffer_limit=None, mode="flush", table=None, obj_list=None)
        except Exception as e: func_runtime_error_record(runtime_error_count=app_state.runtime_error_count, key="buffer_flush", error=e)
    if client_postgres_log_api and buffer_postgres_log_api:
        try:
            async with app_state.runtime_lock_postgres_buffer_flush:
                await app_state.func_postgres_create(client_postgres=client_postgres_log_api, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=app_state.cache_postgres_schema_dict.get(app_state.config_postgres_db_log_api, {}), buffer_postgres=buffer_postgres_log_api, config_column_regex=None, buffer_limit=None, mode="flush", table=None, obj_list=None)
        except Exception as e: func_runtime_error_record(runtime_error_count=app_state.runtime_error_count, key="buffer_flush", error=e)

async def func_postgres_buffer_flush_periodic_task(*, app_state: State, client_postgres: asyncpg.Pool | None, buffer_postgres_create: dict, client_postgres_log_api: Any, buffer_postgres_log_api: dict, interval_sec: int = 60) -> None:
    """Periodically flush all PostgreSQL buffers in a background task loop."""
    while True:
        try:
            await asyncio.sleep(interval_sec)
            await app_state.func_postgres_buffer_flush_all(app_state=app_state, client_postgres=client_postgres, buffer_postgres_create=buffer_postgres_create, client_postgres_log_api=client_postgres_log_api, buffer_postgres_log_api=buffer_postgres_log_api)
        except asyncio.CancelledError: break
        except Exception as e: func_runtime_error_record(runtime_error_count=app_state.runtime_error_count, key="buffer_flush", error=e)
    return

async def func_inmemory_cache_cleanup_periodic_task(*, cache_api_response: dict, cache_ratelimiter: dict, runtime_error_count: dict, cache_token: dict = None, interval_sec: int = 300) -> None:
    """Periodically purges expired items from the in-memory response cache, ratelimiter, and token cache in a background task loop."""
    while True:
        try:
            await asyncio.sleep(interval_sec)
            now = time.time()
            expired_api_keys = [k for k, v in cache_api_response.items() if isinstance(v, dict) and v.get("expire_at", 0) <= now]
            for k in expired_api_keys: cache_api_response.pop(k, None)
            expired_rl_keys = [k for k, v in cache_ratelimiter.items() if isinstance(v, dict) and v.get("expire_at", 0) <= now]
            for k in expired_rl_keys: cache_ratelimiter.pop(k, None)
            for k in [k for k, (_, expires_at) in (cache_token or {}).items() if expires_at <= now]: cache_token.pop(k, None)
        except asyncio.CancelledError: break
        except Exception as e: func_runtime_error_record(runtime_error_count=runtime_error_count, key="cleanup", error=e)
    return

async def func_otp_cleanup(*, conn: asyncpg.Connection, cutoff, timeout_sec: float) -> int:
    """Delete at most 5,000 old OTP rows; leave current codes untouched."""
    result = await conn.execute("DELETE FROM otp WHERE id IN (SELECT id FROM otp WHERE created_at < $1 ORDER BY created_at LIMIT 5000 FOR UPDATE SKIP LOCKED)", cutoff, timeout=timeout_sec)
    return int(result.split()[-1])

async def func_log_api_cleanup(*, conn: asyncpg.Connection, cutoff, timeout_sec: float) -> int:
    """Delete at most 5,000 old API logs from the supplied logging database."""
    result = await conn.execute("DELETE FROM log_api WHERE id IN (SELECT id FROM log_api WHERE created_at < $1 ORDER BY created_at LIMIT 5000 FOR UPDATE SKIP LOCKED)", cutoff, timeout=timeout_sec)
    return int(result.split()[-1])

@asynccontextmanager
async def func_postgres_advisory_lock(*, client_postgres: asyncpg.Pool, lock_id: int):
    """Hold a session advisory lock so only one app worker runs the block at a time; others wait their turn."""
    async with client_postgres.acquire(timeout=30) as conn:
        await conn.execute("SELECT pg_advisory_lock(1096044365, $1)", lock_id)
        try: yield
        finally: await conn.execute("SELECT pg_advisory_unlock(1096044365, $1)", lock_id, timeout=5)

async def func_cleanup_periodic_task(*, client_postgres: asyncpg.Pool, retention_day: int | None, cleanup, lock_id: int, runtime_error_count: dict) -> None:
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
        except Exception as e: func_runtime_error_record(runtime_error_count=runtime_error_count, key="cleanup", error=e)

async def func_async_tasks_cancel(*, task_list: list, timeout_sec: int = 5) -> None:
    """Cancel asynchronous tasks and wait up to the configured timeout for them to finish."""
    task_list = [task for task in task_list if task]
    for task in task_list: task.cancel()
    if task_list: await asyncio.wait(task_list, timeout=timeout_sec)
    return

def func_app_tasks_start(*, app_state: State) -> None:
    """Start the periodic system tasks that func_app_tasks_stop cancels; call after clients and caches are on app_state."""
    app_state.runtime_lock_postgres_buffer_flush = asyncio.Lock()
    postgres_master, client_postgres_log_api = app_state.client_postgres_dict.get("master"), app_state.client_postgres_log_api
    if not app_state.config_is_read_only:
        app_state.runtime_task_postgres_buffer_flush = asyncio.create_task(app_state.func_postgres_buffer_flush_periodic_task(app_state=app_state, client_postgres=postgres_master, buffer_postgres_create=app_state.buffer_postgres_create, client_postgres_log_api=client_postgres_log_api, buffer_postgres_log_api=app_state.buffer_postgres_log_api, interval_sec=app_state.config_postgres_buffer_flush_auto_sec))
        if postgres_master is not None and app_state.config_otp_retention_day is not None:
            app_state.runtime_task_otp_cleanup = asyncio.create_task(app_state.func_cleanup_periodic_task(client_postgres=postgres_master, retention_day=app_state.config_otp_retention_day, cleanup=app_state.func_otp_cleanup, lock_id=1, runtime_error_count=app_state.runtime_error_count))
        if client_postgres_log_api is not None and app_state.config_log_api_retention_day is not None:
            app_state.runtime_task_log_api_cleanup = asyncio.create_task(app_state.func_cleanup_periodic_task(client_postgres=client_postgres_log_api, retention_day=app_state.config_log_api_retention_day, cleanup=app_state.func_log_api_cleanup, lock_id=2, runtime_error_count=app_state.runtime_error_count))
    app_state.runtime_task_inmemory_cache_cleanup = asyncio.create_task(app_state.func_inmemory_cache_cleanup_periodic_task(cache_api_response=app_state.cache_api_response, cache_ratelimiter=app_state.cache_ratelimiter, cache_token=app_state.cache_token, runtime_error_count=app_state.runtime_error_count, interval_sec=app_state.config_inmemory_cache_cleanup_auto_sec))

async def func_app_tasks_stop(*, app_state: State, timeout_sec: int = 5) -> None:
    """Cancel all runtime background tasks and periodic system tasks on app_state."""
    runtime_tasks = list(getattr(app_state, "runtime_background_tasks", set()))
    periodic_tasks = [getattr(app_state, "runtime_task_postgres_buffer_flush", None), getattr(app_state, "runtime_task_inmemory_cache_cleanup", None), getattr(app_state, "runtime_task_otp_cleanup", None), getattr(app_state, "runtime_task_log_api_cleanup", None)]
    await app_state.func_async_tasks_cancel(task_list=runtime_tasks + periodic_tasks, timeout_sec=timeout_sec)
