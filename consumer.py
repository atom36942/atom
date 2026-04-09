#import
from function import *
from config import *
import sys
import asyncio
from itertools import groupby, count

import orjson

#available tasks (for celery registration only)
task_registry = ["func_postgres_create", "func_postgres_update"]

#global counter
_run_counter = count(1)

#dynamic task executor
async def logic_task_exec(pool: any, payload: any) -> any:
    """Dynamically lookup and execute a task function with signature-aware parameter injection."""
    import inspect
    task_name, params = payload.get("task_name"), payload.get("params", {})
    n = next(_run_counter)
    print(f"task started #{n}: {task_name}", flush=True)
    func = globals().get(task_name)
    if not func:
        return print(f"skipping unknown task: {task_name}", flush=True)
    try:
        sig = inspect.signature(func)
        ctx = {"client_postgres_pool": pool, "func_postgres_obj_serialize": func_postgres_obj_serialize}
        call_args = {k: v for k, v in ctx.items() if k in sig.parameters}
        call_args.update({k: v for k, v in params.items() if k in sig.parameters})
        res = await func(**call_args)
        print(f"task completed #{n}: {task_name}", flush=True)
        return res
    except Exception as e:
        print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
        raise

#celery init
def func_consumer_celery_init(consumer_name: str, config_celery_broker_url: str, config_celery_backend_url: str, config_postgres_url: str, config_postgres_min_connection: int, config_postgres_max_connection: int, func_postgres_client_read: callable, func_postgres_create: callable, func_postgres_update: callable, func_postgres_obj_serialize: callable) -> any:
    """Initialize Celery with signature-aware dynamic task registration."""
    from celery import signals
    import inspect
    app = func_celery_client_read_consumer(config_celery_broker_url, config_celery_backend_url)
    app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
    client_postgres_pool, worker_loop = None, None
    async def _init_pool():
        nonlocal client_postgres_pool
        if client_postgres_pool is None:
            client_postgres_pool = await func_postgres_client_read({"dsn": config_postgres_url, "min_size": config_postgres_min_connection, "max_size": config_postgres_max_connection})
    @signals.worker_process_init.connect
    def init_worker(**kwargs):
        nonlocal worker_loop
        worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(worker_loop)
        if config_postgres_url:
            worker_loop.run_until_complete(_init_pool())
    def run_async(coro_func, *args, **kwargs):
        n = next(_run_counter)
        task_name = coro_func.__name__
        print(f"task started #{n}: {task_name}", flush=True)
        nonlocal worker_loop, client_postgres_pool
        if not worker_loop:
            worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
        if client_postgres_pool is None and config_postgres_url:
            worker_loop.run_until_complete(_init_pool())
        try:
            sig = inspect.signature(coro_func)
            ctx = {"client_postgres_pool": client_postgres_pool, "func_postgres_obj_serialize": func_postgres_obj_serialize}
            # 1. Start with injected context parameters
            call_args = {k: v for k, v in ctx.items() if k in sig.parameters}
            # 2. Map positional args to parameters that are NOT in the injected context
            remaining_keys = [p.name for p in sig.parameters.values() if p.name not in call_args]
            call_args.update(dict(zip(remaining_keys, args)))
            # 3. Apply keyword arguments (these take final precedence)
            call_args.update({k: v for k, v in kwargs.items() if k in sig.parameters})
            worker_loop.run_until_complete(coro_func(**call_args))
            print(f"task completed #{n}: {task_name}", flush=True)
            return None
        except Exception as e:
            print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
            raise
    for task_name in task_registry:
        func = globals().get(task_name)
        if not func:
            continue
        @app.task(name=task_name)
        def celery_task(*args, f=func, **kwargs): return run_async(f, *args, **kwargs)
    return app

#technological logic handlers
def logic_celery(channel=None):
    if not channel:
        raise Exception("channel name required")
    name = f"celery_{channel}"
    return func_consumer_celery_init(name, config_celery_broker_url, config_celery_backend_url, config_postgres_url, config_postgres_min_connection, config_postgres_max_connection, func_postgres_client_read, func_postgres_create, func_postgres_update, func_postgres_obj_serialize)

async def logic_redis(channel=None):
    if not channel:
        raise Exception("channel name required")
    pool = await func_postgres_client_read({"dsn": config_postgres_url, "min_size": config_postgres_min_connection, "max_size": config_postgres_max_connection})
    client = await func_redis_client_read(config_redis_url_pubsub)
    reader = await func_redis_client_read_consumer(client, channel)
    print(f"redis consumer started on {channel}", flush=True)
    try:
        async for msg in reader.listen():
            if msg["type"] == "message":
                await logic_task_exec(pool, orjson.loads(msg["data"]))
    finally:
        await client.aclose()
        await pool.close()

async def logic_rabbitmq(channel=None):
    if not channel:
        raise Exception("channel name required")
    pool = await func_postgres_client_read({"dsn": config_postgres_url, "min_size": config_postgres_min_connection, "max_size": config_postgres_max_connection})
    conn, queue = await func_rabbitmq_client_read_consumer(config_rabbitmq_url, channel)
    print(f"rabbitmq consumer started on {channel}", flush=True)
    try:
        async with queue.iterator() as queue_iter:
            async for msg in queue_iter:
                async with msg.process():
                    await logic_task_exec(pool, orjson.loads(msg.body))
    finally:
        await conn.close()
        await pool.close()

async def logic_kafka(channel=None):
    if not channel:
        raise Exception("channel name required")
    pool = await func_postgres_client_read({"dsn": config_postgres_url, "min_size": config_postgres_min_connection, "max_size": config_postgres_max_connection})
    consumer = await func_kafka_client_read_consumer(config_kafka_url, config_kafka_username, config_kafka_password, channel, config_kafka_group_id, config_kafka_is_auto_commit)
    print(f"kafka consumer started on {channel}", flush=True)
    try:
        while True:
            batch = await consumer.getmany(timeout_ms=config_kafka_batch_timeout_ms, max_records=config_kafka_batch_limit)
            if not batch:
                continue
            for tp, messages in batch.items():
                for msg in messages:
                    await logic_task_exec(pool, orjson.loads(msg.value))
                if not config_kafka_is_auto_commit:
                    await consumer.commit(tp)
    finally:
        await consumer.stop()
        await pool.close()

#main
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: venv/bin/python consumer.py [redis|rabbitmq|kafka|celery] [channel]")
        sys.exit(1)
    mode, channel, celery = sys.argv[1], sys.argv[2], None
    if mode == "celery":
        celery = logic_celery(channel)
    try:
        if mode == "redis":
            asyncio.run(logic_redis(channel))
        elif mode == "rabbitmq":
            asyncio.run(logic_rabbitmq(channel))
        elif mode == "kafka":
            asyncio.run(logic_kafka(channel))
        elif mode == "celery":
            celery.worker_main(argv=["worker", "--loglevel=info", "-Q", channel, "-n", f"celery_{channel}@%h"])
        else:
            print(f"unknown mode: {mode}")
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)