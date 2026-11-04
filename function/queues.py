# import
import asyncio
import secrets
import sys
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
        return await client_redis_producer.lpush(channel, orjson.dumps({"payload": payload, "attempt": 0}))
    return None

async def func_queue_redis_recover(*, client: Any, channel: str) -> int:
    """Put back on the queue the jobs a stopped consumer was running: a job stays in <channel>_processing until it is done. Oldest first."""
    moved = 0
    while await client.lmove(f"{channel}_processing", channel, "LEFT", "RIGHT"): moved += 1
    return moved

async def func_queue_redis_job_finish(*, client: Any, channel: str, raw: bytes, error: Exception | None, retry_max: int) -> str:
    """After a Redis job, in one transaction (a job is never in two lists): done → removed from <channel>_processing; failed → back on the queue with attempt + 1, or to <channel>_failed once it has been retried retry_max times. Returns done, retry or failed."""
    try: job = orjson.loads(raw)
    except orjson.JSONDecodeError: job = {"payload": raw.decode("utf-8", "replace"), "attempt": retry_max}    # unreadable: straight to failed
    attempt = job.get("attempt", 0) + 1
    outcome = "done" if error is None else "retry" if attempt <= retry_max else "failed"
    async with client.pipeline(transaction=True) as pipe:
        pipe.lrem(f"{channel}_processing", 1, raw)
        if outcome == "retry": pipe.lpush(channel, orjson.dumps({"payload": job.get("payload"), "attempt": attempt}))
        if outcome == "failed": pipe.lpush(f"{channel}_failed", orjson.dumps({"payload": job.get("payload"), "attempt": attempt, "error": f"{type(error).__name__}: {error}", "failed_at": datetime.now(UTC).isoformat()}))
        await pipe.execute()
    return outcome

async def func_queue_rabbitmq_job_finish(*, rabbitmq_channel: Any, channel: str, message: Any, error: Exception | None, retry_max: int) -> str:
    """After a RabbitMQ job: done → acknowledged; failed → published again with x-attempt + 1, or to <channel>_failed once retried retry_max times, then acknowledged. Returns done, retry or failed."""
    import aio_pika
    attempt = int((message.headers or {}).get("x-attempt", 0)) + 1
    outcome = "done" if error is None else "retry" if attempt <= retry_max else "failed"
    if outcome != "done":
        headers = {"x-attempt": attempt, **({"x-error": f"{type(error).__name__}: {error}"[:1000]} if outcome == "failed" else {})}
        await rabbitmq_channel.default_exchange.publish(aio_pika.Message(body=message.body, headers=headers, delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel if outcome == "retry" else f"{channel}_failed")
    await message.ack()    # after the republish: a crash in between runs the job again rather than losing it
    return outcome

async def func_queue_kafka_job_finish(*, producer: Any, channel: str, message: Any, error: Exception | None, retry_max: int) -> str:
    """After a Kafka job: failed → produced again with header x-attempt + 1, or to topic <channel>_failed once retried retry_max times; the batch's offsets are committed after every job in it is finished. Returns done, retry or failed."""
    attempt = int(dict(message.headers or ()).get("x-attempt", b"0")) + 1
    outcome = "done" if error is None else "retry" if attempt <= retry_max else "failed"
    if outcome != "done":
        headers = [("x-attempt", str(attempt).encode()), *([("x-error", f"{type(error).__name__}: {error}"[:1000].encode())] if outcome == "failed" else [])]
        await producer.send_and_wait(channel if outcome == "retry" else f"{channel}_failed", message.value, headers=headers)
    return outcome

def func_queue_celery_job_finish(*, app: Any, task: Any, channel: str, payload: dict, error: Exception, retry_max: int) -> str:
    """After a failed Celery job: retried by Celery after 1, 2, 4, ... seconds (task.retry raises), or sent to queue <channel>_failed once retried retry_max times. Returns failed."""
    if task.request.retries < retry_max: raise task.retry(exc=error, countdown=2 ** task.request.retries, max_retries=retry_max)
    app.send_task(channel, kwargs=payload, queue=f"{channel}_failed", headers={"x-attempt": task.request.retries + 1, "x-error": f"{type(error).__name__}: {error}"[:1000]})
    return "failed"

def func_run_broker(*, queue: str, channel: str, broker_settings: dict, setup_callback: callable, execute_callback: callable, concurrency: int = 10, retry_max: int = 3):
    if not channel: raise Exception("channel name required")
    url_key = {"redis": "config_redis_url_queue", "rabbitmq": "config_rabbitmq_url", "kafka": "config_kafka_url", "celery": "config_celery_url"}.get(queue)
    if not url_key: raise Exception(f"invalid queue: {queue}; use redis, rabbitmq, kafka or celery")
    if not broker_settings.get(url_key): raise Exception(f"{queue} consumer needs {url_key}: set it in .env")
    _run_counter = count(1)
    if queue == "celery":
        from celery import Celery
        app = Celery("atom", broker=broker_settings.get("config_celery_url"), backend=broker_settings.get("config_celery_url"))
        app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
        setup_data, worker_loop = None, None    # opened by the first job
        def run_async(task, *args, **kwargs):
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
                print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
                func_queue_celery_job_finish(app=app, task=task, channel=channel, payload=payload, error=e, retry_max=retry_max)
                raise
        @app.task(name=channel, bind=True)
        def celery_task(self, *args, **kwargs): return run_async(self, *args, **kwargs)
        app.worker_main(argv=["worker", "--loglevel=info", "--pool=solo", "-Q", channel, "-n", f"celery_{channel}@%h"])    # solo: one process running the asyncio loop; the prefork pool fails every task on Python 3.14
        return
    async def async_runner():
        setup_data = await setup_callback()
        client_primary = setup_data[0]
        semaphore = asyncio.Semaphore(concurrency)
        running = set()    # keeps a reference to each job task until it ends
        async def run_job(n, raw, payload_read):
            """Run one job; returns its error, or None when it succeeded."""
            try:
                await execute_callback(payload_read(raw), *setup_data)
                print(f"task completed #{n}: {channel}", flush=True)
                return None
            except Exception as e:
                print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
                return e
        def job_start(coroutine):
            task = asyncio.create_task(coroutine)
            running.add(task)
            task.add_done_callback(running.discard)
        try:
            if queue == "redis":
                import redis.asyncio as redis
                client = redis.Redis.from_pool(redis.ConnectionPool.from_url(broker_settings.get("config_redis_url_queue"))) if broker_settings.get("config_redis_url_queue") else None
                lock_key, lock_token = f"{channel}_consumer", secrets.token_hex(8)    # one Redis consumer per channel: a second one waits as a standby
                while not await client.set(lock_key, lock_token, nx=True, ex=60):
                    print(f"redis consumer waiting: another consumer runs {channel}", flush=True)
                    await asyncio.sleep(10)
                async def lock_keep():
                    while True:
                        await asyncio.sleep(20)
                        await client.expire(lock_key, 60)
                job_start(lock_keep())
                recovered = await func_queue_redis_recover(client=client, channel=channel)
                print(f"redis consumer started on {channel}" + (f", {recovered} unfinished jobs put back" if recovered else ""), flush=True)
                async def redis_job(n, raw):
                    try:
                        error = await run_job(n, raw, lambda r: orjson.loads(r)["payload"])
                        await func_queue_redis_job_finish(client=client, channel=channel, raw=raw, error=error, retry_max=retry_max)
                    finally: semaphore.release()
                try:
                    while True:
                        await semaphore.acquire()    # take a job only when a worker is free, so waiting jobs stay in Redis, not in memory
                        raw = await client.blmove(channel, f"{channel}_processing", 0, src="RIGHT", dest="LEFT")
                        n = next(_run_counter)
                        print(f"task started #{n}: {channel}", flush=True)
                        job_start(redis_job(n, raw))
                finally:
                    if await client.get(lock_key) == lock_token.encode(): await client.delete(lock_key)
                    await client.aclose()
            elif queue == "rabbitmq":
                import aio_pika
                conn = await aio_pika.connect_robust(broker_settings.get("config_rabbitmq_url"))
                ch = await conn.channel()
                await ch.set_qos(prefetch_count=concurrency)    # RabbitMQ sends at most this many unacknowledged jobs
                rq = await ch.declare_queue(channel, durable=True)
                await ch.declare_queue(f"{channel}_failed", durable=True)
                print(f"rabbitmq consumer started on {channel}", flush=True)
                async def _execute_rmq(n, m):
                    error = await run_job(n, m.body, orjson.loads)
                    await func_queue_rabbitmq_job_finish(rabbitmq_channel=ch, channel=channel, message=m, error=error, retry_max=retry_max)
                try:
                    async with rq.iterator() as queue_iter:
                        async for msg in queue_iter:
                            n = next(_run_counter)
                            print(f"task started #{n}: {channel}", flush=True)
                            job_start(_execute_rmq(n, msg))
                finally:
                    await conn.close()
            elif queue == "kafka":
                from aiokafka import AIOKafkaConsumer
                from aiokafka import AIOKafkaProducer
                url = broker_settings.get("config_kafka_url")
                auth = {"security_protocol": "SASL_SSL", "sasl_mechanism": "PLAIN", "sasl_plain_username": broker_settings.get("config_kafka_username"), "sasl_plain_password": broker_settings.get("config_kafka_password")} if broker_settings.get("config_kafka_username") else {}
                consumer = AIOKafkaConsumer(channel, bootstrap_servers=url, group_id="atom", enable_auto_commit=False, **auth)    # offsets move only after a batch is finished
                producer = AIOKafkaProducer(bootstrap_servers=url, **auth)    # retries and failed jobs
                await consumer.start()
                await producer.start()
                print(f"kafka consumer started on {channel}", flush=True)
                async def kafka_job(msg):
                    n = next(_run_counter)
                    print(f"task started #{n}: {channel}", flush=True)
                    error = await run_job(n, msg.value, orjson.loads)
                    await func_queue_kafka_job_finish(producer=producer, channel=channel, message=msg, error=error, retry_max=retry_max)
                try:
                    while True:
                        batch = await consumer.getmany(timeout_ms=1000, max_records=concurrency)    # at most concurrency jobs at once
                        jobs = [kafka_job(msg) for messages in batch.values() for msg in messages]
                        if not jobs: continue
                        await asyncio.gather(*jobs)
                        await consumer.commit()    # after every job is done, retried or kept: a consumer that stops before this gets the batch again
                finally:
                    await consumer.stop()
                    await producer.stop()
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
    return await func_postgres_create(client_postgres=context["client_postgres"], client_postgres_conn=None, client_password_hasher=context["client_password_hasher"], cache_postgres_schema=context["cache_postgres_schema"], buffer_postgres=context["buffer_postgres_create"], buffer_rows_max=context["config_buffer_rows_max"], buffer_full_mode="reject", config_column_regex=context["config_column_regex"], buffer_limit=context["config_table"].get(table, {}).get("buffer_limit", context["config_buffer_limit_default"]), mode="now", table=table, obj_list=payload.get("obj_list"))    # always now: rows buffered in the consumer would be lost if it stopped after the job counted as done

async def func_consumer_object_update(*, payload: dict, context: dict) -> Any:
    """Channel channel_object_update: the rows PUT /my/object-update?queue=... sent."""
    return await func_postgres_update(client_postgres=context["client_postgres"], client_postgres_conn=None, client_password_hasher=context["client_password_hasher"], cache_postgres_schema=context["cache_postgres_schema"], config_column_regex=context["config_column_regex"], table=payload.get("table"), obj_list=payload.get("obj_list"), created_by_id=payload.get("created_by_id"), ownership_column=payload.get("ownership_column", "created_by_id"))

def func_consumer_channels() -> dict:
    """The only place a channel name maps to the function that handles its messages; producers send on these names."""
    return {"channel_object_create": func_consumer_object_create, "channel_object_update": func_consumer_object_update}

def func_consumer_run(*, queue: str, channel: str, broker_settings: dict, postgres_url: str, config_column_regex: dict, config_table: dict, config_buffer_limit_default: int, config_buffer_rows_max: int, config_queue_concurrency: int = 10, config_queue_retry_max: int = 3):
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
    func_run_broker(queue=queue, channel=channel, broker_settings=broker_settings, setup_callback=setup, execute_callback=execute, concurrency=config_queue_concurrency, retry_max=config_queue_retry_max)
