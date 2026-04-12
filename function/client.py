def func_client_read_gemini(*, config_gemini_key: str) -> any:
    """Initialize Gemini (Generative AI) client with the provided API key."""
    import google.generativeai as genai
    genai.configure(api_key=config_gemini_key)
    return genai

async def func_client_read_postgres(*, config_postgres: dict) -> any:
    """Initialize PostgreSQL connection pool."""
    import asyncpg
    return await asyncpg.create_pool(dsn=config_postgres["dsn"], min_size=config_postgres["min_size"], max_size=config_postgres["max_size"])

async def func_client_read_redis(*, config_redis_url: str) -> any:
    """Initialize Redis client using connection pooling."""
    import redis.asyncio as redis
    return redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))

async def func_client_read_redis_consumer(*, client_redis: any, channel_name: str) -> any:
    """Initialize Redis PubSub consumer and subscribe to a channel."""
    pubsub = client_redis.pubsub()
    await pubsub.subscribe(channel_name)
    return pubsub

def func_client_read_ses(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_ses_region_name: str) -> any:
    """Initialize AWS SES client."""
    import boto3
    return boto3.client("ses", region_name=config_ses_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)

def func_client_read_sns(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_sns_region_name: str) -> any:
    """Initialize AWS SNS client."""
    import boto3
    return boto3.client("sns", region_name=config_sns_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)

async def func_client_read_s3(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_s3_region_name: str) -> any:
    """Initialize AWS S3 client and resource."""
    import aiobotocore.session
    import boto3
    client = aiobotocore.session.get_session().create_client("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
    resource = boto3.resource("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
    return client, resource

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

def func_client_read_openai(*, config_openai_key: str) -> any:
    """Initialize OpenAI client with the provided API key."""
    import openai
    return openai.OpenAI(api_key=config_openai_key)

def func_client_read_posthog(*, config_posthog_project_host: str, config_posthog_project_key: str) -> any:
    """Initialize PostHog client for analytics tracking."""
    from posthog import Posthog
    return Posthog(config_posthog_project_key, host=config_posthog_project_host)

def func_client_read_gsheet(*, config_gsheet_service_account_json_path: str, config_gsheet_scope: list) -> any:
    """Initialize Google Sheets client using a service account credentials file and specific scopes."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(config_gsheet_service_account_json_path, scopes=config_gsheet_scope)
    return gspread.authorize(creds)

def func_client_read_mongodb(*, config_mongodb_uri: str) -> any:
    """Initialize MongoDB client."""
    import motor.motor_asyncio
    return motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_uri)

async def func_client_read_sftp(*, host: str, port: int, username: str, password: str, key_path: str, auth_mode: str) -> any:
    """Initialize SFTP connection using asyncssh."""
    import asyncssh
    if auth_mode not in ("key", "password"):
        raise Exception(f"invalid sftp auth mode: {auth_mode}, allowed: key, password")
    if auth_mode == "key":
        if not key_path:
            raise Exception("ssh key path missing")
        return await asyncssh.connect(host=host, port=int(port), username=username, client_keys=[key_path], known_hosts=None)
    if auth_mode == "password":
        if not password:
            raise Exception("password missing")
        return await asyncssh.connect(host=host, port=int(port), username=username, password=password, known_hosts=None)
