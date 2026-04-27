async def func_orchestrator_producer(*, queue: str, func_name: str, payload: dict, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any) -> any:
    """Ultra-standardized producer orchestration. Handles multi-tech dispatch with explicit clients."""
    import orjson
    if not queue: raise Exception("invalid queue format: queue missing")
    channel = func_name
    allowed_queue = ["redis", "rabbitmq", "kafka", "celery"]
    if queue not in allowed_queue: raise Exception(f"invalid queue: {queue}. allowed: {allowed_queue}")
    if queue == "celery":
        if not client_celery_producer: raise Exception("celery producer not initialized")
        return client_celery_producer.send_task(func_name, kwargs=payload, queue=channel).id
    elif queue == "rabbitmq":
        import aio_pika
        if not client_rabbitmq_producer: raise Exception("rabbitmq producer not initialized")
        return await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(payload), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel)
    elif queue == "kafka":
        if not client_kafka_producer: raise Exception("kafka producer not initialized")
        return await client_kafka_producer.send_and_wait(channel, orjson.dumps(payload))
    elif queue == "redis":
        if not client_redis_producer: raise Exception("redis producer not initialized")
        return await client_redis_producer.publish(channel, orjson.dumps(payload).decode("utf-8"))
    return None
import asyncio

