#import
import sys
import asyncio
import inspect
import orjson
from itertools import count
from ..config import *
from ..function import *

#init
_run_counter = count(1)

#logic
async def broker_logic_redis(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    setup_data = await setup_callback()
    pool = setup_data[0]
    import redis.asyncio as redis
    client = redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url_pubsub)) if config_redis_url_pubsub else None
    reader = client.pubsub()
    await reader.subscribe(channel)
    print(f"redis consumer started on {channel} for {task_name}", flush=True)
    try:
        async for msg in reader.listen():
            if msg["type"] == "message":
                n = next(_run_counter)
                print(f"task started #{n}: {task_name}", flush=True)
                try:
                    await execute_callback(pool, orjson.loads(msg["data"]), *setup_data[1:])
                    print(f"task completed #{n}: {task_name}", flush=True)
                except Exception as e:
                    print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
    finally:
        await client.aclose()
        if pool: await pool.close()

async def broker_logic_rabbitmq(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    setup_data = await setup_callback()
    pool = setup_data[0]
    import aio_pika
    conn = await aio_pika.connect_robust(config_rabbitmq_url)
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=1)
    queue = await ch.declare_queue(channel, durable=True)
    print(f"rabbitmq consumer started on {channel} for {task_name}", flush=True)
    try:
        async with queue.iterator() as queue_iter:
            async for msg in queue_iter:
                async with msg.process():
                    n = next(_run_counter)
                    print(f"task started #{n}: {task_name}", flush=True)
                    try:
                        await execute_callback(pool, orjson.loads(msg.body), *setup_data[1:])
                        print(f"task completed #{n}: {task_name}", flush=True)
                    except Exception as e:
                        print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
    finally:
        await conn.close()
        if pool: await pool.close()

async def broker_logic_kafka(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    setup_data = await setup_callback()
    pool = setup_data[0]
    from aiokafka import AIOKafkaConsumer
    consumer = AIOKafkaConsumer(channel, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit), security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaConsumer(channel, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit))
    await consumer.start()
    print(f"kafka consumer started on {channel} for {task_name}", flush=True)
    try:
        while True:
            batch = await consumer.getmany(timeout_ms=config_kafka_batch_timeout_ms, max_records=config_kafka_batch_limit)
            if not batch: continue
            for tp, messages in batch.items():
                for msg in messages:
                    n = next(_run_counter)
                    print(f"task started #{n}: {task_name}", flush=True)
                    try:
                        await execute_callback(pool, orjson.loads(msg.value), *setup_data[1:])
                        print(f"task completed #{n}: {task_name}", flush=True)
                    except Exception as e:
                        print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
                if not config_kafka_is_auto_commit: await consumer.commit(tp)
    finally:
        await consumer.stop()
        if pool: await pool.close()

def broker_logic_celery(channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    from celery import signals
    consumer_name = f"celery_{channel}"
    from celery import Celery
    app = Celery("atom", broker=config_celery_broker_url, backend=config_celery_backend_url)
    app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
    setup_data, worker_loop = None, None
    @signals.worker_process_init.connect
    def init_worker(**kwargs):
        nonlocal worker_loop, setup_data
        worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(worker_loop)
        setup_data = worker_loop.run_until_complete(setup_callback())
    def run_async(*args, **kwargs):
        n = next(_run_counter)
        print(f"task started #{n}: {task_name}", flush=True)
        nonlocal worker_loop, setup_data
        if not worker_loop:
            worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
            setup_data = worker_loop.run_until_complete(setup_callback())
        try:
            payload = kwargs.get("payload", {}) if "payload" in kwargs else kwargs
            worker_loop.run_until_complete(execute_callback(setup_data[0], payload, *setup_data[1:]))
            print(f"task completed #{n}: {task_name}", flush=True)
            return None
        except Exception as e:
            print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
            raise
    @app.task(name=task_name)
    def celery_task(*args, **kwargs): return run_async(*args, **kwargs)
    return app

#run
def run_broker(mode: str, channel: str, task_name: str, setup_callback: callable, execute_callback: callable):
    celery_app = None
    if mode == "celery": celery_app = broker_logic_celery(channel, task_name, setup_callback, execute_callback)
    try:
        if mode == "redis": asyncio.run(broker_logic_redis(channel, task_name, setup_callback, execute_callback))
        elif mode == "rabbitmq": asyncio.run(broker_logic_rabbitmq(channel, task_name, setup_callback, execute_callback))
        elif mode == "kafka": asyncio.run(broker_logic_kafka(channel, task_name, setup_callback, execute_callback))
        elif mode == "celery": celery_app.worker_main(argv=["worker", "--loglevel=info", "-Q", channel, "-n", f"celery_{channel}@%h"])
        else:
            print(f"unknown mode: {mode}")
            sys.exit(1)
    except KeyboardInterrupt: sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)
