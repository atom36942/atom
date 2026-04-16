def func_client_read_celery_producer(*, config_celery_broker_url: str, config_celery_backend_url: str) -> any:
    """Initialize Celery producer client."""
    from celery import Celery
    return Celery("atom", broker=config_celery_broker_url, backend=config_celery_backend_url)

def func_client_read_celery_consumer(*, config_celery_broker_url: str, config_celery_backend_url: str) -> any:
    """Initialize Celery consumer client."""
    from celery import Celery
    return Celery("atom", broker=config_celery_broker_url, backend=config_celery_backend_url)

async def func_client_read_rabbitmq_producer(*, config_rabbitmq_url: str) -> any:
    """Initialize RabbitMQ producer connection and channel."""
    import aio_pika
    conn = await aio_pika.connect_robust(config_rabbitmq_url)
    channel = await conn.channel()
    return conn, channel

async def func_client_read_rabbitmq_consumer(*, config_rabbitmq_url: str, channel_name: str) -> any:
    """Initialize RabbitMQ consumer connection and queue."""
    import aio_pika
    conn = await aio_pika.connect_robust(config_rabbitmq_url)
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(channel_name, durable=True)
    return conn, queue

async def func_client_read_kafka_producer(*, config_kafka_url: str, config_kafka_username: str, config_kafka_password: str) -> any:
    """Initialize Kafka producer client with optional SASL authentication."""
    from aiokafka import AIOKafkaProducer
    p = AIOKafkaProducer(bootstrap_servers=config_kafka_url, security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaProducer(bootstrap_servers=config_kafka_url)
    await p.start()
    return p

async def func_client_read_kafka_consumer(*, config_kafka_url: str, config_kafka_username: str, config_kafka_password: str, channel_name: str, config_kafka_group_id: str, config_kafka_is_auto_commit: int) -> any:
    """Initialize Kafka consumer client with optional SASL authentication and group settings."""
    from aiokafka import AIOKafkaConsumer
    c = AIOKafkaConsumer(channel_name, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit), security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaConsumer(channel_name, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit))
    await c.start()
    return c
