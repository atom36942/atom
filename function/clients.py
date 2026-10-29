# import
from contextlib import suppress
import asyncpg
import httpx
import redis.asyncio as redis
from argon2 import PasswordHasher
from starlette.datastructures import State

# function
def func_client_password_hasher():
    """Initialize Argon2 password hasher."""
    return PasswordHasher()

def func_client_http():
    """Initialize HTTP async client."""
    return httpx.AsyncClient()

async def func_client_postgres(*, dsn: str, min_size: int = 5, max_size: int = 20, is_read_only: bool = False):
    """Initialize a single asyncpg Postgres connection pool."""
    if not dsn: return None
    pool_kwargs = {"min_size": min_size, "max_size": max_size}
    if is_read_only: pool_kwargs["server_settings"] = {"default_transaction_read_only": "on"}
    return await asyncpg.create_pool(dsn=dsn, **pool_kwargs)

def func_client_redis(*, url: str):
    """Initialize a single Redis connection pool."""
    return redis.Redis.from_pool(redis.ConnectionPool.from_url(url)) if url else None

def func_client_mongodb(*, url: str):
    """Initialize Motor MongoDB client."""
    if not url: return None
    import motor.motor_asyncio
    return motor.motor_asyncio.AsyncIOMotorClient(url)

async def func_client_mssql(*, dsn: str, min_size: int = 1, max_size: int = 10, recycle_sec: int = 1800):
    """Initialize MSSQL connection pool; idle connections older than recycle_sec are reopened. Autocommit: aioodbc returns a connection to the pool without a rollback, so a read or a failed write must not leave a transaction open for the next request."""
    if not dsn: return None
    import pyodbc
    import aioodbc
    pyodbc.pooling = False
    return await aioodbc.create_pool(dsn=dsn, minsize=min_size, maxsize=max_size, pool_recycle=recycle_sec, autocommit=True)

async def func_client_clickhouse(*, dsn: str):
    """Initialize ClickHouse async client."""
    if not dsn: return None
    import clickhouse_connect
    return await clickhouse_connect.get_async_client(dsn=dsn)

async def func_client_s3(*, region_name: str, aws_access_key_id: str, aws_secret_access_key: str):
    """Initialize AWS S3 async botocore client session."""
    if not region_name: return None
    import aiobotocore.session
    s3_context = aiobotocore.session.get_session().create_client("s3", region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    s3_client = await s3_context.__aenter__()
    s3_client._context = s3_context
    return s3_client

def func_client_s3_resource(*, region_name: str, aws_access_key_id: str, aws_secret_access_key: str):
    """Initialize AWS S3 boto3 resource."""
    if not region_name: return None
    import boto3
    return boto3.resource("s3", region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

def func_client_sns(*, region_name: str, aws_access_key_id: str, aws_secret_access_key: str):
    """Initialize AWS SNS boto3 client."""
    if not region_name: return None
    import boto3
    return boto3.client("sns", region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

def func_client_ses(*, region_name: str, aws_access_key_id: str, aws_secret_access_key: str):
    """Initialize AWS SES boto3 client."""
    if not region_name: return None
    import boto3
    return boto3.client("ses", region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

def func_client_openai(*, api_key: str):
    """Initialize OpenAI client."""
    if not api_key: return None
    import openai
    return openai.OpenAI(api_key=api_key)

def func_client_gemini(*, api_key: str):
    """Initialize Google Gemini client."""
    if not api_key: return None
    from google import genai
    return genai.Client(api_key=api_key)

def func_client_posthog(*, project_key: str, host: str):
    """Initialize PostHog client."""
    if not project_key: return None
    from posthog import Posthog
    return Posthog(project_key, host=host)

def func_client_celery(*, url: str):
    """Initialize Celery producer client."""
    if not url: return None
    from celery import Celery
    return Celery("atom", broker=url, backend=url)

async def func_client_kafka(*, url: str, username: str = None, password: str = None):
    """Initialize and start AIOKafkaProducer."""
    if not url: return None
    from aiokafka import AIOKafkaProducer
    producer = (AIOKafkaProducer(bootstrap_servers=url, security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=username, sasl_plain_password=password) if username else AIOKafkaProducer(bootstrap_servers=url))
    await producer.start()
    return producer

async def func_client_rabbitmq(*, url: str):
    """Initialize aio_pika RabbitMQ robust connection and channel."""
    if not url: return None, None
    import aio_pika
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    return connection, channel

async def func_client_sftp(*, host: str, port: int, username: str, password: str):
    """Initialize SFTP asyncssh connection."""
    if not host: return None
    import asyncssh
    return await asyncssh.connect(host=host, port=int(port), username=username, password=password, known_hosts=None)

def func_client_azure_email(*, connection_string: str):
    """Initialize Azure EmailClient."""
    if not connection_string: return None
    from azure.communication.email import EmailClient
    return EmailClient.from_connection_string(connection_string)

def func_client_azure_sms(*, connection_string: str):
    """Initialize Azure SmsClient."""
    if not connection_string: return None
    from azure.communication.sms import SmsClient
    return SmsClient.from_connection_string(connection_string)

def func_client_azure_blob(*, account_name: str, account_key: str):
    """Initialize Azure BlobServiceClient."""
    if not (account_name and account_key): return None
    from azure.storage.blob.aio import BlobServiceClient
    return BlobServiceClient.from_connection_string(f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net")

def func_client_msgraph(*, tenant_id: str, client_id: str, client_secret: str, scopes: list = None):
    """Initialize Microsoft Graph ServiceClient (Flow 1: Client Credentials)."""
    if not (tenant_id and client_id and client_secret): return None
    from azure.identity import ClientSecretCredential
    from msgraph import GraphServiceClient
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    scopes = scopes or ["https://graph.microsoft.com/.default"]
    return GraphServiceClient(credentials=credential, scopes=scopes)

async def func_client_close(*, app_state: State = None, clients: dict = None) -> None:
    """Safely disconnect and close all active database, storage, messaging, and AI clients."""
    c = {}
    if app_state: c = {k: getattr(app_state, k, None) for k in dir(app_state) if k.startswith("client_")}
    elif isinstance(clients, dict): c = clients.copy()
    client_http = c.get("client_http")
    if client_http:
        with suppress(Exception): await client_http.aclose()
    client_postgres_dict = c.get("client_postgres_dict") or {}
    for client_postgres_item in client_postgres_dict.values():
        if client_postgres_item:
            with suppress(Exception): await client_postgres_item.close()
    client_postgres_pgweb = c.get("client_postgres_pgweb") or {}
    for client_postgres_session in client_postgres_pgweb.values():
        if client_postgres_session:
            with suppress(Exception): await client_postgres_session.close()
    for r_client in (c.get("client_redis_dict") or {}).values():
        if r_client:
            with suppress(Exception): await r_client.aclose()
    client_mongodb = c.get("client_mongodb")
    if client_mongodb:
        with suppress(Exception): client_mongodb.close()
    for client_mssql in (c.get("client_mssql_dict") or {}).values():
        if client_mssql:
            with suppress(Exception):
                client_mssql.close()
                await client_mssql.wait_closed()
    for client_clickhouse in (c.get("client_clickhouse_dict") or {}).values():
        if client_clickhouse:
            with suppress(Exception): await client_clickhouse.close()
    client_s3 = c.get("client_s3")
    if client_s3:
        s3_ctx = getattr(client_s3, "_context", None)
        if s3_ctx:
            with suppress(Exception): await s3_ctx.__aexit__(None, None, None)
    client_s3_resource = c.get("client_s3_resource")
    if client_s3_resource and hasattr(client_s3_resource.meta.client, "close"):
        with suppress(Exception): client_s3_resource.meta.client.close()
    for boto_key in ("client_sns", "client_ses"):
        b_client = c.get(boto_key)
        if b_client and hasattr(b_client, "close"):
            with suppress(Exception): b_client.close()
    for ai_key in ("client_openai", "client_gemini"):
        ai_client = c.get(ai_key)
        if ai_client and hasattr(ai_client, "close"):
            with suppress(Exception): ai_client.close()
    client_posthog = c.get("client_posthog")
    if client_posthog:
        with suppress(Exception):
            client_posthog.shutdown()
            client_posthog.flush()
    client_celery = c.get("client_celery_producer")
    if client_celery and hasattr(client_celery, "close"):
        with suppress(Exception): client_celery.close()
    client_kafka = c.get("client_kafka_producer")
    if client_kafka:
        with suppress(Exception): await client_kafka.stop()
    client_rabbitmq_producer = c.get("client_rabbitmq_producer")
    if client_rabbitmq_producer and not getattr(client_rabbitmq_producer, "is_closed", True):
        with suppress(Exception): await client_rabbitmq_producer.close()
    client_rabbitmq = c.get("client_rabbitmq")
    if client_rabbitmq and not getattr(client_rabbitmq, "is_closed", True):
        with suppress(Exception): await client_rabbitmq.close()
    client_sftp = c.get("client_sftp")
    if client_sftp:
        with suppress(Exception):
            client_sftp.close()
            await client_sftp.wait_closed()
    client_azure_email = c.get("client_azure_email")
    if client_azure_email and hasattr(client_azure_email, "close"):
        with suppress(Exception): client_azure_email.close()
    client_azure_sms = c.get("client_azure_sms")
    if client_azure_sms and hasattr(client_azure_sms, "close"):
        with suppress(Exception): client_azure_sms.close()
    client_azure_blob = c.get("client_azure_blob")
    if client_azure_blob:
        with suppress(Exception): await client_azure_blob.close()
