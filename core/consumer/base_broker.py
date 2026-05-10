#import
import sys
import asyncio
import orjson
import os
import traceback
from datetime import datetime, timezone
from itertools import count
from ..config import *

#init
_run_counter = count(1)

#log
def _payload_log_value(payload: any) -> any:
    if isinstance(payload, bytes):
        try: return payload.decode("utf-8")
        except Exception: return repr(payload)
    return payload

def func_consumer_failed_payload_log(*, queue: str, channel: str, payload: any, error: Exception) -> None:
    os.makedirs("tmp", exist_ok=True)
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "queue": queue,
        "channel": channel,
        "payload": _payload_log_value(payload),
        "error_type": type(error).__name__,
        "error": str(error),
        "traceback": traceback.format_exc()
    }
    with open("tmp/consumer_failed_payload.jsonl", "ab") as file:
        file.write(orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE))

#logic
async def broker_logic_redis(channel: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    setup_data = await setup_callback()
    client_primary = setup_data[0]
    import redis.asyncio as redis
    client = redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url_pubsub)) if config_redis_url_pubsub else None
    print(f"redis consumer started on {channel}", flush=True)
    semaphore = asyncio.Semaphore(config_consumer_concurrency)
    async def _execute(n, p):
        async with semaphore:
            try:
                p_obj = orjson.loads(p)
                await execute_callback(client_primary, p_obj, *setup_data[1:])
                print(f"task completed #{n}: {channel}", flush=True)
            except Exception as e:
                func_consumer_failed_payload_log(queue="redis", channel=channel, payload=p, error=e)
                print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
    try:
        while True:
            msg = await client.brpop(channel, timeout=0)
            if msg:
                n = next(_run_counter)
                print(f"task started #{n}: {channel}", flush=True)
                asyncio.create_task(_execute(n, msg[1]))
    finally:
        await client.aclose()
        if client_primary: await client_primary.close()

async def broker_logic_rabbitmq(channel: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    setup_data = await setup_callback()
    client_primary = setup_data[0]
    import aio_pika
    conn = await aio_pika.connect_robust(config_rabbitmq_url)
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=config_consumer_concurrency)
    queue = await ch.declare_queue(channel, durable=True)
    print(f"rabbitmq consumer started on {channel}", flush=True)
    semaphore = asyncio.Semaphore(config_consumer_concurrency)
    async def _execute(n, m):
        async with semaphore:
            async with m.process():
                p = m.body
                try:
                    p_obj = orjson.loads(p)
                    await execute_callback(client_primary, p_obj, *setup_data[1:])
                    print(f"task completed #{n}: {channel}", flush=True)
                except Exception as e:
                    func_consumer_failed_payload_log(queue="rabbitmq", channel=channel, payload=p, error=e)
                    print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
    try:
        async with queue.iterator() as queue_iter:
            async for msg in queue_iter:
                n = next(_run_counter)
                print(f"task started #{n}: {channel}", flush=True)
                asyncio.create_task(_execute(n, msg))
    finally:
        await conn.close()
        if client_primary: await client_primary.close()

async def broker_logic_kafka(channel: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    setup_data = await setup_callback()
    client_primary = setup_data[0]
    from aiokafka import AIOKafkaConsumer
    consumer = AIOKafkaConsumer(channel, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit), security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaConsumer(channel, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit))
    await consumer.start()
    print(f"kafka consumer started on {channel}", flush=True)
    semaphore = asyncio.Semaphore(config_consumer_concurrency)
    async def _execute(n, p):
        async with semaphore:
            try:
                p_obj = orjson.loads(p)
                await execute_callback(client_primary, p_obj, *setup_data[1:])
                print(f"task completed #{n}: {channel}", flush=True)
            except Exception as e:
                func_consumer_failed_payload_log(queue="kafka", channel=channel, payload=p, error=e)
                print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
    try:
        while True:
            batch = await consumer.getmany(timeout_ms=config_kafka_batch_timeout_ms, max_records=config_kafka_batch_limit)
            if not batch: continue
            for tp, messages in batch.items():
                tasks = []
                for msg in messages:
                    n = next(_run_counter)
                    print(f"task started #{n}: {channel}", flush=True)
                    tasks.append(asyncio.create_task(_execute(n, msg.value)))
                if tasks: await asyncio.gather(*tasks)
                if not config_kafka_is_auto_commit: await consumer.commit(tp)
    finally:
        await consumer.stop()
        if client_primary: await client_primary.close()

def broker_logic_celery(channel: str, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    from celery import signals
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
        print(f"task started #{n}: {channel}", flush=True)
        nonlocal worker_loop, setup_data
        payload = kwargs.get("payload", {}) if "payload" in kwargs else kwargs
        if not worker_loop:
            worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
            setup_data = worker_loop.run_until_complete(setup_callback())
        try:
            worker_loop.run_until_complete(execute_callback(setup_data[0], payload, *setup_data[1:]))
            print(f"task completed #{n}: {channel}", flush=True)
            return None
        except Exception as e:
            func_consumer_failed_payload_log(queue="celery", channel=channel, payload=payload, error=e)
            print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
            raise
    @app.task(name=channel)
    def celery_task(*args, **kwargs): return run_async(*args, **kwargs)
    return app

#run
def run_broker(queue: str, channel: str, setup_callback: callable, execute_callback: callable):
    celery_app = None
    if queue == "celery": celery_app = broker_logic_celery(channel, setup_callback, execute_callback)
    try:
        if queue == "redis": asyncio.run(broker_logic_redis(channel, setup_callback, execute_callback))
        elif queue == "rabbitmq": asyncio.run(broker_logic_rabbitmq(channel, setup_callback, execute_callback))
        elif queue == "kafka": asyncio.run(broker_logic_kafka(channel, setup_callback, execute_callback))
        elif queue == "celery": celery_app.worker_main(argv=["worker", "--loglevel=info", "-Q", channel, "-n", f"celery_{channel}@%h"])
        else:
            print(f"unknown queue: {queue}")
            sys.exit(1)
    except KeyboardInterrupt: sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)
