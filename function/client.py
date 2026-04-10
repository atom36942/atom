async def func_postgres_client_read(config_postgres: dict) -> any:
    """Initialize PostgreSQL connection pool."""
    import asyncpg
    return await asyncpg.create_pool(dsn=config_postgres["dsn"], min_size=config_postgres["min_size"], max_size=config_postgres["max_size"])

async def func_redis_client_read(url: str) -> any:
    """Initialize Redis client using aioredis."""
    import redis.asyncio as redis
    client = redis.from_url(url, decode_responses=True)
    return client

async def func_redis_client_read_consumer(client: any, channel: str) -> any:
    """Initialize Redis pubsub consumer."""
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub

def func_gemini_client_read(api_key: str) -> any:
    """Initialize Google Gemini AI client."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai

def func_openai_client_read(api_key: str) -> any:
    """Initialize OpenAI API client."""
    from openai import OpenAI
    return OpenAI(api_key=api_key)

def func_posthog_client_read(host: str, api_key: str) -> any:
    """Initialize PostHog analytics client."""
    from posthog import Posthog
    return Posthog(api_key, host=host)

def func_gsheet_client_read(service_account_json: str, scope: list) -> any:
    """Initialize Google Sheets client using a service account JSON file."""
    import gspread, orjson
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_info(orjson.loads(service_account_json), scopes=scope)
    return gspread.authorize(creds)

def func_mongodb_client_read(uri: str) -> any:
    """Initialize MongoDB client using motor."""
    from motor.motor_asyncio import AsyncIOMotorClient
    return AsyncIOMotorClient(uri)

async def func_sftp_client_read(host: str, port: int, username: str, password: str, key_path: str, auth_mode: str) -> any:
    """Initialize SFTP client using paramiko."""
    import paramiko
    transport = paramiko.Transport((host, port))
    if auth_mode == "password":
        transport.connect(username=username, password=password)
    else:
        key = paramiko.RSAKey.from_private_key_file(key_path)
        transport.connect(username=username, pkey=key)
    return paramiko.SFTPClient.from_transport(transport)

async def func_s3_client_read(access_key: str, secret_key: str, region_name: str) -> any:
    """Initialize Aiobotocore S3 client and resource."""
    import aiobotocore.session
    session = aiobotocore.session.get_session()
    async with session.create_client("s3", region_name=region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_key) as client:
        return client, session

def func_sns_client_read(access_key: str, secret_key: str, region_name: str) -> any:
    """Initialize Boto3 SNS client."""
    import boto3
    return boto3.client("sns", region_name=region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

def func_ses_client_read(access_key: str, secret_key: str, region_name: str) -> any:
    """Initialize Boto3 SES client."""
    import boto3
    return boto3.client("ses", region_name=region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

def func_celery_client_read_producer(broker_url: str, backend_url: str) -> any:
    """Initialize Celery Application for producer."""
    from celery import Celery
    return Celery("atom", broker=broker_url, backend=backend_url)

def func_celery_client_read_consumer(broker_url: str, backend_url: str) -> any:
    """Initialize Celery Application for consumer."""
    from celery import Celery
    return Celery("atom", broker=broker_url, backend=backend_url)

async def func_kafka_client_read_producer(bootstrap_servers: str, username: str = None, password: str = None) -> any:
    """Initialize AIOKafkaProducer."""
    from aiokafka import AIOKafkaProducer
    import ssl
    context = ssl.create_default_context()
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers, security_protocol="SASL_SSL" if username else "PLAINTEXT", sasl_mechanism="PLAIN", sasl_plain_username=username, sasl_plain_password=password, ssl_context=context if username else None)
    await producer.start()
    return producer

async def func_kafka_client_read_consumer(bootstrap_servers: str, username: str, password: str, topic: str, group_id: str, is_auto_commit: int) -> any:
    """Initialize AIOKafkaConsumer."""
    from aiokafka import AIOKafkaConsumer
    import ssl
    context = ssl.create_default_context()
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=bootstrap_servers, security_protocol="SASL_SSL" if username else "PLAINTEXT", sasl_mechanism="PLAIN", sasl_plain_username=username, sasl_plain_password=password, ssl_context=context if username else None, group_id=group_id, auto_offset_reset="earliest", enable_auto_commit=bool(is_auto_commit))
    await consumer.start()
    return consumer

async def func_rabbitmq_client_read_producer(url: str) -> tuple:
    """Initialize RabbitMQ connection and channel for producer."""
    import aio_pika
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    return connection, channel

async def func_rabbitmq_client_read_consumer(url: str, queue_name: str) -> tuple:
    """Initialize RabbitMQ connection and queue for consumer."""
    import aio_pika
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    queue = await channel.declare_queue(queue_name, durable=True)
    return connection, queue

def func_celery_producer(channel: str, task_name: str, client_celery_producer: any, params: dict) -> str:
    """Dispatch a task to Celery."""
    client_celery_producer.send_task(task_name, args=[], kwargs=params, queue=channel)
    return "queued celery"

async def func_kafka_producer(channel: str, client_kafka_producer: any, task_obj: dict) -> str:
    """Dispatch a task to Kafka."""
    import orjson
    await client_kafka_producer.send_and_wait(channel, orjson.dumps(task_obj))
    return "queued kafka"

async def func_rabbitmq_producer(channel: str, client_rabbitmq_producer: any, task_obj: dict) -> str:
    """Dispatch a task to RabbitMQ."""
    import aio_pika, orjson
    await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(task_obj)), routing_key=channel)
    return "queued rabbitmq"

def func_consumer_celery_init(consumer_name: str, config_celery_broker_url: str, config_celery_backend_url: str, config_postgres_url: str, config_postgres_min_connection: int, config_postgres_max_connection: int, func_postgres_client_read: callable, func_postgres_create: callable, func_postgres_update: callable, func_postgres_obj_serialize: callable, task_registry: list = None, task_map: dict = None) -> any:
    """Initialize Celery with signature-aware dynamic task registration."""
    from celery import signals
    import inspect, asyncio
    app = func_celery_client_read_consumer(config_celery_broker_url, config_celery_backend_url)
    app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
    client_postgres_pool, worker_loop = None, None
    task_registry = task_registry or []
    task_map = task_map or {}
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
        import time
        from itertools import count
        _run_counter = count(1)
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
            call_args = {k: v for k, v in ctx.items() if k in sig.parameters}
            remaining_keys = [p.name for p in sig.parameters.values() if p.name not in call_args]
            call_args.update(dict(zip(remaining_keys, args)))
            call_args.update({k: v for k, v in kwargs.items() if k in sig.parameters})
            worker_loop.run_until_complete(coro_func(**call_args))
            print(f"task completed #{n}: {task_name}", flush=True)
            return None
        except Exception as e:
            print(f"task failed #{n}: {task_name} error: {str(e)}", flush=True)
            raise
    for task_name in task_registry:
        func = task_map.get(task_name)
        if not func:
            continue
        @app.task(name=task_name)
        def celery_task(*args, f=func, **kwargs): return run_async(f, *args, **kwargs)
    return app
