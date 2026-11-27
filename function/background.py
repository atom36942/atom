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

def func_postgres_buffer_flush_interval(*, app_state: State, connection: str) -> int:
    """Seconds between periodic flushes of one database's buffered rows: config_postgres_buffer_flush_auto_sec_<name>, else config_postgres_buffer_flush_auto_sec."""
    return int(getattr(app_state, f"config_postgres_buffer_flush_auto_sec_{connection}", None) or app_state.config_postgres_buffer_flush_auto_sec)

async def func_postgres_buffer_flush_all(*, app_state: State, connections: set = None) -> None:
    """Flush the create buffer and the log_api buffer, each database's rows through its own pool (the key's connection); connections limits it to those databases.
    A database without a pool, or a failed insert, keeps its rows for the next flush and is counted under buffer_flush; the other databases are still flushed."""
    for buffer in (app_state.buffer_postgres_create, app_state.buffer_postgres_log_api):
        for name in sorted({app_state.func_postgres_buffer_key_read(key=key)["connection"] for key in list(buffer)}):
            if connections is not None and name not in connections: continue
            try:
                client_postgres = app_state.client_postgres_dict.get(name)
                if not client_postgres: raise Exception(f"buffered rows for '{name}' wait: no pool (config_postgres_url_{name} is not set)")
                async with app_state.runtime_lock_postgres_buffer_flush:
                    await app_state.func_postgres_create(client_postgres=client_postgres, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=app_state.cache_postgres_schema_dict.get(name, {}), buffer_postgres=buffer, config_column_regex=None, buffer_limit=None, mode="flush", table=None, obj_list=None, connection=name)
            except Exception as e: func_runtime_error_record(runtime_error_count=app_state.runtime_error_count, key="buffer_flush", error=e)

async def func_postgres_buffer_flush_periodic_task(*, app_state: State) -> None:
    """Flush buffered rows in a background loop, each database every func_postgres_buffer_flush_interval seconds (config_postgres_buffer_flush_auto_sec_<name>, else config_postgres_buffer_flush_auto_sec)."""
    names = set(app_state.client_postgres_dict)
    tick = min(func_postgres_buffer_flush_interval(app_state=app_state, connection=name) for name in names | {"master"})
    flushed_at = {name: time.monotonic() for name in names}
    while True:
        try:
            await asyncio.sleep(tick)
            now = time.monotonic()
            due = {name for name in names if now - flushed_at[name] >= func_postgres_buffer_flush_interval(app_state=app_state, connection=name) - tick / 2}    # half a tick early, so sleep's drift never skips a round
            if due: await app_state.func_postgres_buffer_flush_all(app_state=app_state, connections=due)
            for name in due: flushed_at[name] = now
        except asyncio.CancelledError: break
        except Exception as e: func_runtime_error_record(runtime_error_count=app_state.runtime_error_count, key="buffer_flush", error=e)
    return

async def func_inmemory_cache_cleanup_periodic_task(*, cache_api_response: dict, cache_ratelimiter: dict, runtime_error_count: dict, cache_token: dict = None, cache_api_response_bytes: dict = None, interval_sec: int = 300) -> None:
    """Periodically purges expired items from the in-memory response cache, ratelimiter, and token cache in a background task loop."""
    while True:
        try:
            await asyncio.sleep(interval_sec)
            now = time.time()
            expired_api_keys = [k for k, v in cache_api_response.items() if isinstance(v, dict) and v.get("expire_at", 0) <= now]
            for k in expired_api_keys:
                if (item := cache_api_response.pop(k, None)) and cache_api_response_bytes is not None: cache_api_response_bytes["total"] -= len(item["data"])
            expired_rl_keys = [k for k, v in cache_ratelimiter.items() if isinstance(v, dict) and v.get("expire_at", 0) <= now]
            for k in expired_rl_keys: cache_ratelimiter.pop(k, None)
            for k in [k for k, (_, expires_at) in (cache_token or {}).items() if expires_at <= now]: cache_token.pop(k, None)
        except asyncio.CancelledError: break
        except Exception as e: func_runtime_error_record(runtime_error_count=runtime_error_count, key="cleanup", error=e)
    return

async def func_otp_cleanup(*, conn: asyncpg.Connection, cutoff, timeout_sec: float) -> int:
    """Delete at most 5,000 OTP rows older than cutoff; leave current codes untouched (script/postgres_cleanup.py calls it until done)."""
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
        finally:
            try: await conn.execute("SELECT pg_advisory_unlock(1096044365, $1)", lock_id, timeout=5)
            except Exception: conn.terminate()    # pools skip the reset query, so a lock that cannot be released ends with its session

async def func_async_tasks_cancel(*, task_list: list, timeout_sec: int = 5) -> None:
    """Cancel asynchronous tasks and wait up to the configured timeout for them to finish."""
    task_list = [task for task in task_list if task]
    for task in task_list: task.cancel()
    if task_list: await asyncio.wait(task_list, timeout=timeout_sec)
    return

def func_app_tasks_start(*, app_state: State) -> None:
    """Start the periodic system tasks that func_app_tasks_stop cancels; call after clients and caches are on app_state."""
    app_state.runtime_lock_postgres_buffer_flush = asyncio.Lock()
    postgres_master = app_state.client_postgres_dict.get("master")
    if not app_state.config_is_read_only:
        app_state.runtime_task_postgres_buffer_flush = asyncio.create_task(app_state.func_postgres_buffer_flush_periodic_task(app_state=app_state))
        schedules = app_state.func_schedule_read(values=getattr(app_state, "_state", None) or vars(app_state))
        if postgres_master is not None and schedules:
            app_state.runtime_task_schedule = asyncio.create_task(app_state.func_schedule_periodic_task(client_postgres=postgres_master, schedules=schedules, timezone=app_state.func_schedule_timezone(name=app_state.config_schedule_timezone), runtime_error_count=app_state.runtime_error_count))
        if postgres_master is not None and app_state.config_webhook_is_active:
            app_state.runtime_task_webhook = asyncio.create_task(app_state.func_webhook_deliver_periodic_task(client_postgres=postgres_master, client_http=app_state.client_http, runtime_error_count=app_state.runtime_error_count))
    app_state.runtime_task_memory_history = asyncio.create_task(app_state.func_memory_history_periodic_task(app_state=app_state))
    app_state.runtime_task_inmemory_cache_cleanup = asyncio.create_task(app_state.func_inmemory_cache_cleanup_periodic_task(cache_api_response=app_state.cache_api_response, cache_api_response_bytes=app_state.cache_api_response_bytes, cache_ratelimiter=app_state.cache_ratelimiter, cache_token=app_state.cache_token, runtime_error_count=app_state.runtime_error_count))

async def func_app_tasks_stop(*, app_state: State, timeout_sec: int = 5) -> None:
    """Cancel all runtime background tasks and periodic system tasks on app_state."""
    runtime_tasks = list(getattr(app_state, "runtime_background_tasks", set()))
    periodic_tasks = [getattr(app_state, "runtime_task_postgres_buffer_flush", None), getattr(app_state, "runtime_task_inmemory_cache_cleanup", None), getattr(app_state, "runtime_task_schedule", None), getattr(app_state, "runtime_task_webhook", None), getattr(app_state, "runtime_task_memory_history", None)]
    await app_state.func_async_tasks_cancel(task_list=runtime_tasks + periodic_tasks, timeout_sec=timeout_sec)
