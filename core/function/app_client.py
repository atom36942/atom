
async def func_client_read_postgres(*, config_postgres: dict) -> any:
    """Initialize PostgreSQL connection pool and log status."""
    if not config_postgres.get("dsn"):
        print(f"🐘 {'postgres client':<30} : ❌ config missing")
        return None
    try:
        import asyncpg
        res = await asyncpg.create_pool(dsn=config_postgres["dsn"], min_size=config_postgres["min_size"], max_size=config_postgres["max_size"])
        print(f"🐘 {'postgres client':<30} : ✅ connected")
        return res
    except Exception as e:
        print(f"🐘 {'postgres client':<30} : ❌ error: {str(e)[:30]}")
        return None

async def func_client_read_mongodb(*, config_mongodb_url: str) -> any:
    """Initialize MongoDB client and log status."""
    if not config_mongodb_url:
        print(f"🍃 {'mongodb client':<30} : ❌ config missing")
        return None
    try:
        import motor.motor_asyncio
        res = motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
        print(f"🍃 {'mongodb client':<30} : ✅ connected")
        return res
    except Exception as e:
        print(f"🍃 {'mongodb client':<30} : ❌ error: {str(e)[:30]}")
        return None

def func_client_read_gemini(*, config_gemini_key: str) -> any:
    """Initialize Gemini client and log status."""
    if not config_gemini_key:
        print(f"♊ {'gemini client':<30} : ❌ config missing")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=config_gemini_key)
        print(f"♊ {'gemini client':<30} : ✅ initialized")
        return genai
    except Exception as e:
        print(f"♊ {'gemini client':<30} : ❌ error: {str(e)[:30]}")
        return None

def func_client_read_openai(*, config_openai_key: str) -> any:
    """Initialize OpenAI client and log status."""
    if not config_openai_key:
        print(f"🤖 {'openai client':<30} : ❌ config missing")
        return None
    try:
        import openai
        res = openai.OpenAI(api_key=config_openai_key)
        print(f"🤖 {'openai client':<30} : ✅ initialized")
        return res
    except Exception as e:
        print(f"🤖 {'openai client':<30} : ❌ error: {str(e)[:30]}")
        return None

def func_client_read_ses(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_ses_region_name: str) -> any:
    """Initialize AWS SES client and log status."""
    if not config_ses_region_name:
        print(f"📧 {'aws ses client':<30} : ❌ config missing")
        return None
    try:
        import boto3
        res = boto3.client("ses", region_name=config_ses_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
        print(f"📧 {'aws ses client':<30} : ✅ connected")
        return res
    except Exception as e:
        print(f"📧 {'aws ses client':<30} : ❌ error: {str(e)[:30]}")
        return None

def func_client_read_sns(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_sns_region_name: str) -> any:
    """Initialize AWS SNS client and log status."""
    if not config_sns_region_name:
        print(f"🔔 {'aws sns client':<30} : ❌ config missing")
        return None
    try:
        import boto3
        res = boto3.client("sns", region_name=config_sns_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_sns_region_name)
        print(f"🔔 {'aws sns client':<30} : ✅ connected")
        return res
    except Exception as e:
        print(f"🔔 {'aws sns client':<30} : ❌ error: {str(e)[:30]}")
        return None

async def func_client_read_s3(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_s3_region_name: str) -> any:
    """Initialize AWS S3 client and resource and log status."""
    if not config_s3_region_name:
        print(f"☁️  {'aws s3 client':<30} : ❌ config missing")
        return None, None
    try:
        import aiobotocore.session
        import boto3
        client = aiobotocore.session.get_session().create_client("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
        resource = boto3.resource("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
        print(f"☁️  {'aws s3 client':<30} : ✅ connected")
        return client, resource
    except Exception as e:
        print(f"☁️  {'aws s3 client':<30} : ❌ error: {str(e)[:30]}")
        return None, None

async def func_client_read_redis(*, config_redis_url: str, event_name: str = "🔴 redis client") -> any:
    """Initialize Redis client and log status."""
    if not config_redis_url:
        print(f"{event_name[0]} {event_name[2:]:<30} : ❌ config missing")
        return None
    try:
        import redis.asyncio as redis
        res = redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))
        print(f"{event_name[0]} {event_name[2:]:<30} : ✅ connected")
        return res
    except Exception as e:
        print(f"{event_name[0]} {event_name[2:]:<30} : ❌ error: {str(e)[:30]}")
        return None

async def func_client_read_redis_consumer(*, client_redis: any, channel_name: str) -> any:
    """Initialize Redis PubSub consumer and subscribe to a channel."""
    if not client_redis:
        return None
    pubsub = client_redis.pubsub()
    await pubsub.subscribe(channel_name)
    return pubsub

def func_client_read_celery_producer(*, config_celery_broker_url: str, config_celery_backend_url: str) -> any:
    """Initialize Celery producer client and log status."""
    if not config_celery_broker_url:
        print(f"📦 {'celery producer':<30} : ❌ config missing")
        return None
    try:
        from celery import Celery
        res = Celery("atom", broker=config_celery_broker_url, backend=config_celery_backend_url)
        print(f"📦 {'celery producer':<30} : ✅ initialized")
        return res
    except Exception as e:
        print(f"📦 {'celery producer':<30} : ❌ error: {str(e)[:30]}")
        return None

def func_client_read_celery_consumer(*, config_celery_broker_url: str, config_celery_backend_url: str) -> any:
    """Initialize Celery consumer client."""
    from celery import Celery
    return Celery("atom", broker=config_celery_broker_url, backend=config_celery_backend_url)

async def func_client_read_rabbitmq_producer(*, config_rabbitmq_url: str) -> any:
    """Initialize RabbitMQ producer connection and channel and log status."""
    if not config_rabbitmq_url:
        print(f"🐇 {'rabbitmq client':<30} : ❌ config missing")
        return None, None
    try:
        import aio_pika
        conn = await aio_pika.connect_robust(config_rabbitmq_url)
        channel = await conn.channel()
        print(f"🐇 {'rabbitmq client':<30} : ✅ connected")
        return conn, channel
    except Exception as e:
        print(f"🐇 {'rabbitmq client':<30} : ❌ error: {str(e)[:30]}")
        return None, None

async def func_client_read_rabbitmq_consumer(*, config_rabbitmq_url: str, channel_name: str) -> any:
    """Initialize RabbitMQ consumer connection and queue."""
    import aio_pika
    conn = await aio_pika.connect_robust(config_rabbitmq_url)
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(channel_name, durable=True)
    return conn, queue

async def func_client_read_kafka_producer(*, config_kafka_url: str, config_kafka_username: str, config_kafka_password: str) -> any:
    """Initialize Kafka producer client and log status."""
    if not config_kafka_url:
        print(f"🎡 {'kafka client':<30} : ❌ config missing")
        return None
    try:
        from aiokafka import AIOKafkaProducer
        p = AIOKafkaProducer(bootstrap_servers=config_kafka_url, security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaProducer(bootstrap_servers=config_kafka_url)
        await p.start()
        print(f"🎡 {'kafka client':<30} : ✅ connected")
        return p
    except Exception as e:
        print(f"🎡 {'kafka client':<30} : ❌ error: {str(e)[:30]}")
        return None

async def func_client_read_kafka_consumer(*, config_kafka_url: str, config_kafka_username: str, config_kafka_password: str, channel_name: str, config_kafka_group_id: str, config_kafka_is_auto_commit: int) -> any:
    """Initialize Kafka consumer client."""
    from aiokafka import AIOKafkaConsumer
    c = AIOKafkaConsumer(channel_name, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit), security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaConsumer(channel_name, bootstrap_servers=config_kafka_url, group_id=config_kafka_group_id, enable_auto_commit=bool(config_kafka_is_auto_commit))
    await c.start()
    return c

def func_client_read_posthog(*, config_posthog_project_host: str, config_posthog_project_key: str) -> any:
    """Initialize PostHog client and log status."""
    if not config_posthog_project_key:
        print(f"🦔 {'posthog client':<30} : ❌ config missing")
        return None
    try:
        from posthog import Posthog
        res = Posthog(config_posthog_project_key, host=config_posthog_project_host)
        print(f"🦔 {'posthog client':<30} : ✅ initialized")
        return res
    except Exception as e:
        print(f"🦔 {'posthog client':<30} : ❌ error: {str(e)[:30]}")
        return None

def func_client_read_gsheet(*, config_gsheet_service_account_json_path: str, config_gsheet_scope: list) -> any:
    """Initialize Google Sheets client and log status."""
    if not config_gsheet_service_account_json_path:
        print(f"📊 {'gsheet client':<30} : ❌ config missing")
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(config_gsheet_service_account_json_path, scopes=config_gsheet_scope)
        res = gspread.authorize(creds)
        print(f"📊 {'gsheet client':<30} : ✅ initialized")
        return res
    except Exception as e:
        print(f"📊 {'gsheet client':<30} : ❌ error: {str(e)[:30]}")
        return None

async def func_client_read_sftp(*, config_sftp_host: str, config_sftp_port: int, config_sftp_username: str, config_sftp_password: str, config_sftp_key_path: str, config_sftp_auth_method: str) -> any:
    """Initialize SFTP connection and log status."""
    if not config_sftp_host:
        print(f"📁 {'sftp client':<30} : ❌ config missing")
        return None
    try:
        import asyncssh
        if config_sftp_auth_method not in ("key", "password"):
            raise Exception(f"invalid sftp auth mode: {config_sftp_auth_method}")
        if config_sftp_auth_method == "key":
            if not config_sftp_key_path:
                raise Exception("ssh key path missing")
            res = await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, client_keys=[config_sftp_key_path], known_hosts=None)
        else:
            if not config_sftp_password:
                raise Exception("password missing")
            res = await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, password=config_sftp_password, known_hosts=None)
        print(f"📁 {'sftp client':<30} : ✅ connected")
        return res
    except Exception as e:
        print(f"📁 {'sftp client':<30} : ❌ error: {str(e)[:30]}")
        return None
