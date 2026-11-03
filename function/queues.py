# import
import asyncio
import os
import sys
import traceback
from datetime import datetime
from datetime import UTC
from itertools import count
from typing import Any
import orjson
from .clients import func_client_password_hasher
from .clients import func_client_postgres
from .middleware import func_api_error
from .postgres_crud import func_postgres_create
from .postgres_crud import func_postgres_update
from .postgres_metadata import func_postgres_schema_read

# function
async def func_producer(*, queue: str, client_celery_producer: Any, client_kafka_producer: Any, client_rabbitmq_producer: Any, client_redis_producer: Any, channel: str, payload: dict) -> Any:
    """Ultra-standardized producer orchestration. Handles multi-tech dispatch with explicit clients."""
    allowed_queue_services = ["redis", "rabbitmq", "kafka", "celery"]
    if not queue: raise Exception("invalid queue format: queue missing")
    if queue not in allowed_queue_services: raise Exception(f"invalid queue: {queue}. allowed: {allowed_queue_services}")
    if queue == "celery":
        if not client_celery_producer: raise func_api_error(message="celery producer not initialized", status_code=500)
        return (await asyncio.to_thread(client_celery_producer.send_task, channel, kwargs=payload, queue=channel)).id
    if queue == "rabbitmq":
        import aio_pika
        if not client_rabbitmq_producer: raise func_api_error(message="rabbitmq producer not initialized", status_code=500)
        return await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(payload), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel)
    if queue == "kafka":
        if not client_kafka_producer: raise func_api_error(message="kafka producer not initialized", status_code=500)
        return await client_kafka_producer.send_and_wait(channel, orjson.dumps(payload))
    if queue == "redis":
        if not client_redis_producer: raise func_api_error(message="redis producer not initialized", status_code=500)
        return await client_redis_producer.lpush(channel, orjson.dumps(payload).decode("utf-8"))
    return None

def func_run_broker(*, queue: str, channel: str, broker_settings: dict, setup_callback: callable, execute_callback: callable):
    if not channel: raise Exception("channel name required")
    url_key = {"redis": "config_redis_url_queue", "rabbitmq": "config_rabbitmq_url", "kafka": "config_kafka_url", "celery": "config_celery_url"}.get(queue)
    if not url_key: raise Exception(f"invalid queue: {queue}; use redis, rabbitmq, kafka or celery")
    if not broker_settings.get(url_key): raise Exception(f"{queue} consumer needs {url_key}: set it in .env")
    _run_counter = count(1)
    def log_failure(q, p, e):
        os.makedirs("tmp", exist_ok=True)
        try: payload_str = p.decode("utf-8") if isinstance(p, bytes) else p
        except Exception: payload_str = repr(p)
        record = {"time": datetime.now(UTC).isoformat(), "queue": q, "channel": channel, "payload": payload_str, "error_type": type(e).__name__, "error": str(e), "traceback": traceback.format_exc()}
        with open("tmp/consumer_failed_payload.jsonl", "ab") as file: file.write(orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE))
    if queue == "celery":
        from celery import signals
        from celery import Celery
        app = Celery("atom", broker=broker_settings.get("config_celery_url"), backend=broker_settings.get("config_celery_url"))
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
                worker_loop.run_until_complete(execute_callback(payload, *setup_data))
                print(f"task completed #{n}: {channel}", flush=True)
                return
            except Exception as e:
                log_failure("celery", payload, e)
                print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
                raise
        @app.task(name=channel)
        def celery_task(*args, **kwargs): return run_async(*args, **kwargs)
        app.worker_main(argv=["worker", "--loglevel=info", "-Q", channel, "-n", f"celery_{channel}@%h"])
        return
    async def async_runner():
        setup_data = await setup_callback()
        client_primary = setup_data[0]
        consumer_concurrency = 10
        semaphore = asyncio.Semaphore(consumer_concurrency)
        async def _execute(n, p):
            async with semaphore:
                try:
                    p_obj = orjson.loads(p)
                    await execute_callback(p_obj, *setup_data)
                    print(f"task completed #{n}: {channel}", flush=True)
                except Exception as e:
                    await asyncio.to_thread(log_failure, queue, p, e)
                    print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
        try:
            if queue == "redis":
                import redis.asyncio as redis
                client = redis.Redis.from_pool(redis.ConnectionPool.from_url(broker_settings.get("config_redis_url_queue"))) if broker_settings.get("config_redis_url_queue") else None
                print(f"redis consumer started on {channel}", flush=True)
                try:
                    while True:
                        msg = await client.brpop(channel, timeout=0)
                        if msg:
                            n = next(_run_counter)
                            print(f"task started #{n}: {channel}", flush=True)
                            asyncio.create_task(_execute(n, msg[1]))
                finally:
                    await client.aclose()
            elif queue == "rabbitmq":
                import aio_pika
                conn = await aio_pika.connect_robust(broker_settings.get("config_rabbitmq_url"))
                ch = await conn.channel()
                await ch.set_qos(prefetch_count=consumer_concurrency)
                rq = await ch.declare_queue(channel, durable=True)
                print(f"rabbitmq consumer started on {channel}", flush=True)
                async def _execute_rmq(n, m):
                    async with m.process():
                        await _execute(n, m.body)
                try:
                    async with rq.iterator() as queue_iter:
                        async for msg in queue_iter:
                            n = next(_run_counter)
                            print(f"task started #{n}: {channel}", flush=True)
                            asyncio.create_task(_execute_rmq(n, msg))
                finally:
                    await conn.close()
            elif queue == "kafka":
                from aiokafka import AIOKafkaConsumer
                kafka_group_id = "atom"
                kafka_is_enable_auto_commit = 1
                kafka_batch_limit = 100
                kafka_batch_timeout_ms = 1000
                if broker_settings.get("config_kafka_username"):
                    consumer = AIOKafkaConsumer(channel, bootstrap_servers=broker_settings.get("config_kafka_url"), group_id=kafka_group_id, enable_auto_commit=bool(kafka_is_enable_auto_commit), security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=broker_settings.get("config_kafka_username"), sasl_plain_password=broker_settings.get("config_kafka_password"))
                else:
                    consumer = AIOKafkaConsumer(channel, bootstrap_servers=broker_settings.get("config_kafka_url"), group_id=kafka_group_id, enable_auto_commit=bool(kafka_is_enable_auto_commit))
                await consumer.start()
                print(f"kafka consumer started on {channel}", flush=True)
                try:
                    while True:
                        batch = await consumer.getmany(timeout_ms=kafka_batch_timeout_ms, max_records=kafka_batch_limit)
                        if not batch: continue
                        for tp, messages in batch.items():
                            tasks = []
                            for msg in messages:
                                n = next(_run_counter)
                                print(f"task started #{n}: {channel}", flush=True)
                                tasks.append(asyncio.create_task(_execute(n, msg.value)))
                            if tasks: await asyncio.gather(*tasks)
                            if not kafka_is_enable_auto_commit: await consumer.commit(tp)
                finally:
                    await consumer.stop()
            else:
                print(f"unknown queue: {queue}")
                sys.exit(1)
        finally:
            if client_primary: await client_primary.close()
    try: asyncio.run(async_runner())
    except KeyboardInterrupt: sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)

async def func_consumer_object_create(*, payload: dict, context: dict) -> Any:
    """Channel channel_object_create: the rows POST /my/object-create?queue=... sent."""
    table = payload.get("table")
    return await func_postgres_create(client_postgres=context["client_postgres"], client_postgres_conn=None, client_password_hasher=context["client_password_hasher"], cache_postgres_schema=context["cache_postgres_schema"], buffer_postgres=context["buffer_postgres_create"], buffer_rows_max=context["config_buffer_rows_max"], buffer_full_mode="reject", config_column_regex=context["config_column_regex"], buffer_limit=context["config_table"].get(table, {}).get("buffer_limit", context["config_buffer_limit_default"]), mode=payload.get("mode", "now"), table=table, obj_list=payload.get("obj_list"))

async def func_consumer_object_update(*, payload: dict, context: dict) -> Any:
    """Channel channel_object_update: the rows PUT /my/object-update?queue=... sent."""
    return await func_postgres_update(client_postgres=context["client_postgres"], client_postgres_conn=None, client_password_hasher=context["client_password_hasher"], cache_postgres_schema=context["cache_postgres_schema"], config_column_regex=context["config_column_regex"], table=payload.get("table"), obj_list=payload.get("obj_list"), created_by_id=payload.get("created_by_id"), ownership_column=payload.get("ownership_column", "created_by_id"))

def func_consumer_channels() -> dict:
    """The only place a channel name maps to the function that handles its messages; producers send on these names."""
    return {"channel_object_create": func_consumer_object_create, "channel_object_update": func_consumer_object_update}

def func_consumer_run(*, queue: str, channel: str, broker_settings: dict, postgres_url: str, config_column_regex: dict, config_table: dict, config_buffer_limit_default: int, config_buffer_rows_max: int):
    """Runs one consumer process: listens on channel through queue and hands each message to that channel's function."""
    handler = func_consumer_channels().get(channel)
    if not handler: raise Exception(f"unknown channel: {channel}; use one of {', '.join(func_consumer_channels())}")
    if not postgres_url: raise Exception("consumer needs config_postgres_url_master: set it in .env")
    async def setup():
        client_postgres = await func_client_postgres(dsn=postgres_url, min_size=1, max_size=5)
        context = {"client_postgres": client_postgres, "client_password_hasher": func_client_password_hasher(), "cache_postgres_schema": await func_postgres_schema_read(client_postgres=client_postgres), "buffer_postgres_create": {}, "config_column_regex": config_column_regex, "config_table": config_table, "config_buffer_limit_default": config_buffer_limit_default, "config_buffer_rows_max": config_buffer_rows_max}
        return client_postgres, context    # func_run_broker closes the first item on exit
    async def execute(payload, client_postgres, context):
        return await handler(payload=payload, context=context)
    func_run_broker(queue=queue, channel=channel, broker_settings=broker_settings, setup_callback=setup, execute_callback=execute)
