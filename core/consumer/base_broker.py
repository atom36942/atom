import sys
import asyncio
import inspect
from itertools import count

from ..config import *
from ..function import *

_run_counter = count(1)

async def broker_logic_redis(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    import orjson
    if not channel:
        raise Exception("channel name required")
    pool, buffer, schema = await setup_callback()
    client = await func_client_read_redis(config_redis_url=config_redis_url_pubsub)
    reader = await func_client_read_redis_consumer(client_redis=client, channel_name=channel)
    print(f"redis consumer started on {channel} for {task_name}", flush=True)
    try:
        async for msg in reader.listen():
            if msg["type"] == "message":
                n = next(_run_counter)
                print(f"task started #{n}: {task_name}", flush=True)
                try:
                    await execute_callback(pool, orjson.loads(msg["data"]), buffer, schema)
                    print(f"task completed #{n}: {task_name}", flush=True)
                except Exception as e:
                    print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
    finally:
        await client.aclose()
        if pool:
            await pool.close()

async def broker_logic_rabbitmq(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    import orjson
    if not channel:
        raise Exception("channel name required")
    pool, buffer, schema = await setup_callback()
    conn, queue = await func_client_read_rabbitmq_consumer(config_rabbitmq_url=config_rabbitmq_url, channel_name=channel)
    print(f"rabbitmq consumer started on {channel} for {task_name}", flush=True)
    try:
        async with queue.iterator() as queue_iter:
            async for msg in queue_iter:
                async with msg.process():
                    n = next(_run_counter)
                    print(f"task started #{n}: {task_name}", flush=True)
                    try:
                        await execute_callback(pool, orjson.loads(msg.body), buffer, schema)
                        print(f"task completed #{n}: {task_name}", flush=True)
                    except Exception as e:
                        print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
    finally:
        await conn.close()
        if pool:
            await pool.close()

async def broker_logic_kafka(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    import orjson
    if not channel:
        raise Exception("channel name required")
    pool, buffer, schema = await setup_callback()
    consumer = await func_client_read_kafka_consumer(config_kafka_url=config_kafka_url, config_kafka_username=config_kafka_username, config_kafka_password=config_kafka_password, channel_name=channel, config_kafka_group_id=config_kafka_group_id, config_kafka_is_auto_commit=config_kafka_is_auto_commit)
    print(f"kafka consumer started on {channel} for {task_name}", flush=True)
    try:
        while True:
            batch = await consumer.getmany(timeout_ms=config_kafka_batch_timeout_ms, max_records=config_kafka_batch_limit)
            if not batch:
                continue
            for tp, messages in batch.items():
                for msg in messages:
                    n = next(_run_counter)
                    print(f"task started #{n}: {task_name}", flush=True)
                    try:
                        await execute_callback(pool, orjson.loads(msg.value), buffer, schema)
                        print(f"task completed #{n}: {task_name}", flush=True)
                    except Exception as e:
                        print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
                if not config_kafka_is_auto_commit:
                    await consumer.commit(tp)
    finally:
        await consumer.stop()
        if pool:
            await pool.close()

def broker_logic_celery(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    if not channel:
        raise Exception("channel name required")
    from celery import signals
    consumer_name = f"celery_{channel}"
    app = func_client_read_celery_consumer(config_celery_broker_url=config_celery_broker_url, config_celery_backend_url=config_celery_backend_url)
    app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
    
    pool, buffer, schema, worker_loop = None, {}, {}, None
    
    @signals.worker_process_init.connect
    def init_worker(**kwargs):
        nonlocal worker_loop, pool, buffer, schema
        worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(worker_loop)
        pool, buffer, schema = worker_loop.run_until_complete(setup_callback())

    def run_async(*args, **kwargs):
        n = next(_run_counter)
        print(f"task started #{n}: {task_name}", flush=True)
        nonlocal worker_loop, pool, buffer, schema
        if not worker_loop:
            worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
            pool, buffer, schema = worker_loop.run_until_complete(setup_callback())
        try:
            # Handle payload mapping
            payload = kwargs.get("payload", {}) if "payload" in kwargs else kwargs
            worker_loop.run_until_complete(execute_callback(pool, payload, buffer, schema))
            print(f"task completed #{n}: {task_name}", flush=True)
            return None
        except Exception as e:
            print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
            raise

    @app.task(name=task_name)
    def celery_task(*args, **kwargs):
        return run_async(*args, **kwargs)

    return app

def run_broker(mode: str, channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    celery_app = None
    if mode == "celery":
        celery_app = broker_logic_celery(channel, task_name, setup_callback, execute_callback)
    
    try:
        if mode == "redis":
            asyncio.run(broker_logic_redis(channel, task_name, setup_callback, execute_callback))
        elif mode == "rabbitmq":
            asyncio.run(broker_logic_rabbitmq(channel, task_name, setup_callback, execute_callback))
        elif mode == "kafka":
            asyncio.run(broker_logic_kafka(channel, task_name, setup_callback, execute_callback))
        elif mode == "celery":
            celery_app.worker_main(argv=["worker", "--loglevel=info", "-Q", channel, "-n", f"celery_{channel}@%h"])
        else:
            print(f"unknown mode: {mode}")
            sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)
