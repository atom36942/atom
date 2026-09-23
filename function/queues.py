"""Atom queues functions."""

async def func_producer(*, queue: str, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, channel: str, payload: dict) -> any:
    """Ultra-standardized producer orchestration. Handles multi-tech dispatch with explicit clients."""
    import orjson
    allowed_queue_services = ["redis", "rabbitmq", "kafka", "celery"]
    if not queue: raise Exception("invalid queue format: queue missing")
    if queue not in allowed_queue_services: raise Exception(f"invalid queue: {queue}. allowed: {allowed_queue_services}")
    if queue == "celery":
        if not client_celery_producer: raise Exception("celery producer not initialized")
        return client_celery_producer.send_task(channel, kwargs=payload, queue=channel).id
    elif queue == "rabbitmq":
        import aio_pika
        if not client_rabbitmq_producer: raise Exception("rabbitmq producer not initialized")
        return await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(payload), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel)
    elif queue == "kafka":
        if not client_kafka_producer: raise Exception("kafka producer not initialized")
        return await client_kafka_producer.send_and_wait(channel, orjson.dumps(payload))
    elif queue == "redis":
        if not client_redis_producer: raise Exception("redis producer not initialized")
        return await client_redis_producer.lpush(channel, orjson.dumps(payload).decode("utf-8"))
    return None

def func_run_broker(*, queue: str, channel: str, broker_settings: dict, setup_callback: callable, execute_callback: callable):
    import sys, asyncio, orjson, os, traceback
    from datetime import datetime, timezone
    from itertools import count
    if not channel: raise Exception("channel name required")
    _run_counter = count(1)
    def log_failure(q, p, e):
        os.makedirs("tmp", exist_ok=True)
        try: payload_str = p.decode("utf-8") if isinstance(p, bytes) else p
        except Exception: payload_str = repr(p)
        record = {"time": datetime.now(timezone.utc).isoformat(), "queue": q, "channel": channel, "payload": payload_str, "error_type": type(e).__name__, "error": str(e), "traceback": traceback.format_exc()}
        with open("tmp/consumer_failed_payload.jsonl", "ab") as file: file.write(orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE))
    if queue == "celery":
        from celery import signals, Celery
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
                return None
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
