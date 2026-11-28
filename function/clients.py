# import
import asyncio
from contextlib import asynccontextmanager
import inspect
import asyncpg
from asyncpg.pool import Pool
from asyncpg.pool import PoolConnectionProxy
import httpx
import redis.asyncio as redis
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from starlette.datastructures import State

# function
def func_client_password_hasher():
    """Initialize Argon2 password hasher."""
    return PasswordHasher()

def func_client_http():
    """Initialize HTTP async client."""
    return httpx.AsyncClient()

def func_client_pool_size(*, app_state: State, db: str, name: str) -> dict:
    """{"min_size", "max_size"} of one database's pool: config_<db>_pool_min_size_<name> / config_<db>_pool_max_size_<name> when set, else the shared config_<db>_pool_min_size / config_<db>_pool_max_size. db: postgres or mssql."""
    return {f"{size}_size": int(getattr(app_state, f"config_{db}_pool_{size}_size_{name}", None) or getattr(app_state, f"config_{db}_pool_{size}_size")) for size in ("min", "max")}

async def func_client_dict_open(*, url_dict: dict, client_open, client_close) -> dict:
    """Open one client per named URL at once (client_open(name=, url=)), skipping empty URLs; returns name -> client. When one fails, or startup is cancelled, the ones that opened are closed (client_close(client)) and the error is raised, so nothing is left open."""
    names = [name for name, url in (url_dict or {}).items() if url]
    tasks = [asyncio.ensure_future(client_open(name=name, url=url_dict[name])) for name in names]
    def opened(): return {name: task.result() for name, task in zip(names, tasks, strict=True) if task.done() and not task.cancelled() and task.exception() is None}
    try: await asyncio.gather(*tasks, return_exceptions=True)
    except BaseException:
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await func_client_dict_close(clients=opened(), client_close=client_close)
        raise
    if errors := [task.exception() for task in tasks if task.exception() is not None]:
        await func_client_dict_close(clients=opened(), client_close=client_close)
        raise errors[0]
    return opened()

async def func_client_dict_close(*, clients: dict, client_close) -> None:
    """Close every client of a named dict (client_close(client), sync or async); one failing is printed and the others still close."""
    for name, client in (clients or {}).items():
        try:
            result = client_close(client)
            if inspect.isawaitable(result): await result
        except Exception as e: print(f"❌ close {name}: {e}")

class _FairPool(Pool):
    """asyncpg pool that hands connections to waiting requests in the order they asked: a request first takes a place at a first-come-first-served gate (asyncio.Semaphore, one place per connection), so a request that just arrived never takes a freed connection ahead of one already waiting. Without it, a connection released without a reset query goes back so fast that new requests overtake waiting ones: about the same throughput, but a slow tail (p95 at 50 users on 10 connections: 46 vs 18 ms; at 200 users: 242 vs 91 ms)."""
    __slots__ = ("_gate", "atom_read_only")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gate = asyncio.Semaphore(kwargs["max_size"])
        self.atom_read_only = (kwargs.get("server_settings") or {}).get("default_transaction_read_only") == "on"    # every transaction on it is read-only: callers skip BEGIN READ ONLY

    async def _acquire(self, timeout):  # noqa: ASYNC109 - asyncpg's own signature, overridden
        async with asyncio.timeout(timeout):
            await self._gate.acquire()
            try: return await super()._acquire(timeout)
            except BaseException:
                self._gate.release()
                raise

    async def release(self, connection, *, timeout=None):  # noqa: ASYNC109 - asyncpg's own signature, overridden
        is_held = type(connection) is PoolConnectionProxy and connection._holder._pool is self and connection._con is not None
        try: return await super().release(connection, timeout=timeout)
        finally:
            if is_held: self._gate.release()

async def func_client_postgres(*, dsn: str, min_size: int = 5, max_size: int = 20, is_read_only: bool = False, query_timeout_sec: float = 0):
    """Initialize a single asyncpg Postgres connection pool; query_timeout_sec above 0 cancels any query running longer (asyncpg command_timeout, the query is cancelled on the server too). A released connection skips asyncpg's reset query (RESET ALL, UNLISTEN, unlock): Atom's code leaves no session state, an open transaction is still rolled back, and SQL someone typed runs through func_postgres_acquire_clean, so each request saves a round trip. Waiting requests get connections in the order they asked (_FairPool)."""
    if not dsn: return None
    async def keep_session(conn): return None
    pool_kwargs = {"min_size": min_size, "max_size": max_size, "reset": keep_session}
    if is_read_only: pool_kwargs["server_settings"] = {"default_transaction_read_only": "on"}
    if query_timeout_sec: pool_kwargs["command_timeout"] = query_timeout_sec
    # the same arguments asyncpg.create_pool passes, with its defaults
    return await _FairPool(dsn, connection_class=asyncpg.Connection, record_class=asyncpg.Record, max_queries=50000, max_inactive_connection_lifetime=300.0, loop=None, **pool_kwargs)

POSTGRES_RESET_TASKS = set()    # resets running after their request answered; kept so they are not garbage collected

async def func_postgres_reset_release(*, acquire_context, conn) -> None:
    """Reset a borrowed connection's session (rolls back an open transaction, RESET ALL, UNLISTEN, unlocks), close it when that fails, then give it back to the pool (leaving its acquire context)."""
    try: await conn.reset(timeout=5)
    except Exception: conn.terminate()
    finally: await acquire_context.__aexit__(None, None, None)

@asynccontextmanager
async def func_postgres_acquire_clean(*, client_postgres: asyncpg.Pool):
    """Borrow a pool connection for SQL someone typed (query runners, pgweb): its session (SET, SET ROLE, advisory locks, LISTEN) is reset before it goes back, and a connection that cannot be reset is closed.
    The reset runs in the background once the caller is done, so the response does not wait for its round trip; the pool gets the connection back only when it is clean."""
    acquire_context = client_postgres.acquire()
    conn = await acquire_context.__aenter__()
    try: yield conn
    finally:
        task = asyncio.create_task(func_postgres_reset_release(acquire_context=acquire_context, conn=conn))
        POSTGRES_RESET_TASKS.add(task)
        task.add_done_callback(POSTGRES_RESET_TASKS.discard)

def func_client_redis(*, url: str, max_connections: int = 100, timeout_sec: float = 5, key_prefix: str = ""):
    """Initialize a single Redis connection pool: when all max_connections are busy, a command waits up to timeout_sec for one instead of failing at once. key_prefix (kept on the client as atom_key_prefix) starts every cache, user-state and rate-limit key, so apps sharing one Redis never read each other's keys."""
    if not url: return None
    client = redis.Redis.from_pool(redis.BlockingConnectionPool.from_url(url, max_connections=max_connections, timeout=timeout_sec))
    client.atom_key_prefix = key_prefix
    return client

def func_redis_key_prefix(*, postgres_url: str | None) -> str:
    """The app's Redis key prefix: its master database name and a colon (shop -> "shop:"), "" without one. Apps on one Redis have different databases, so their keys differ with nothing to set."""
    try: parts = urlsplit(postgres_url or "")
    except ValueError: return ""
    name = parts.path.strip("/") if parts.scheme else ""
    return f"{name}:" if name else ""

def func_redis_key(*, client_redis, key: str) -> str:
    """A Redis key with the client's app prefix (func_client_redis key_prefix); unchanged for a client without one or None (the in-memory modes)."""
    return getattr(client_redis, "atom_key_prefix", "") + key

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

def func_client_anthropic(*, api_key: str):
    """Initialize the async Anthropic (Claude) client."""
    if not api_key: return None
    import anthropic
    return anthropic.AsyncAnthropic(api_key=api_key)

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
    try: channel = await connection.channel()
    except BaseException:
        await connection.close()
        raise
    return connection, channel

async def func_client_sftp(*, host: str, port: int, username: str, password: str, known_hosts_path: str | None = None, is_host_verify: bool = True):
    """Initialize SFTP asyncssh connection. The server's key is checked against known_hosts_path (default ~/.ssh/known_hosts), so a server pretending to be it is refused; is_host_verify=False skips the check."""
    if not host: return None
    import asyncssh
    known_hosts = (known_hosts_path or ()) if is_host_verify else None    # () is asyncssh's default file
    return await asyncssh.connect(host=host, port=int(port), username=username, password=password, known_hosts=known_hosts)

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

async def func_rabbitmq_close(*, connection, channel) -> None:
    """Close the RabbitMQ producer channel, then its connection."""
    if channel is not None and not getattr(channel, "is_closed", True): await channel.close()
    if connection is not None and not getattr(connection, "is_closed", True): await connection.close()

async def func_mssql_close(*, client) -> None:
    """Close an aioodbc pool and wait for its connections to close."""
    client.close()
    await client.wait_closed()

async def func_sftp_close(*, client) -> None:
    """Close an asyncssh connection and wait for it to close."""
    client.close()
    await client.wait_closed()

def func_client_sync_close(*, client) -> None:
    """Close a client whose close() is optional and sync (boto3, OpenAI, Gemini, Celery, Azure email and SMS)."""
    if hasattr(client, "close"): client.close()

def func_client_registry(*, app_state: State) -> dict:
    """Atom's clients: name -> (open, close). open() returns the client, or None when its settings are empty (its SDK is then never imported); close(client) may be sync or async, None when there is nothing to close. Each client is defined here once: startup opens them all at once, shutdown and a failed startup close them."""
    s = app_state
    aws = {"aws_access_key_id": s.config_aws_access_key_id, "aws_secret_access_key": s.config_aws_secret_access_key}
    redis_key_prefix = func_redis_key_prefix(postgres_url=getattr(s, "config_postgres_url_master", None) or (s.config_postgres_url_dict or {}).get("master"))    # the master database name: apps sharing one Redis keep apart
    rabbitmq = {}    # the connection behind the producer channel, closed with it
    async def rabbitmq_open():
        connection, channel = await func_client_rabbitmq(url=s.config_rabbitmq_url)
        rabbitmq["connection"] = connection
        return channel
    return {
        "client_password_hasher": (lambda: func_client_password_hasher(), None),
        "client_http": (lambda: func_client_http(), lambda c: c.aclose()),
        # pool sizes per database: config_<db>_pool_min_size_<name> / config_<db>_pool_max_size_<name> when set, else the shared config_<db>_pool_min_size / config_<db>_pool_max_size
        "client_postgres_dict": (lambda: func_client_dict_open(url_dict=s.config_postgres_url_dict, client_open=lambda name, url: func_client_postgres(dsn=url, **func_client_pool_size(app_state=s, db="postgres", name=name), is_read_only=s.config_is_read_only, query_timeout_sec=s.config_postgres_query_timeout_sec), client_close=lambda c: c.close()), lambda d: func_client_dict_close(clients=d, client_close=lambda c: c.close())),
        "client_postgres_pgweb": (lambda: {}, lambda d: func_client_dict_close(clients=d, client_close=lambda c: c.close())),    # pgweb sessions, opened on demand
        "client_redis_dict": (lambda: {name: func_client_redis(url=url, key_prefix=redis_key_prefix) for name, url in (s.config_redis_url_dict or {}).items() if url}, lambda d: func_client_dict_close(clients=d, client_close=lambda c: c.aclose())),
        "client_mssql_dict": (lambda: func_client_dict_open(url_dict=s.config_mssql_url_dict, client_open=lambda name, url: func_client_mssql(dsn=url, **func_client_pool_size(app_state=s, db="mssql", name=name), recycle_sec=s.config_mssql_pool_recycle_sec), client_close=lambda c: func_mssql_close(client=c)), lambda d: func_client_dict_close(clients=d, client_close=lambda c: func_mssql_close(client=c))),
        "client_clickhouse_dict": (lambda: func_client_dict_open(url_dict=s.config_clickhouse_url_dict, client_open=lambda name, url: func_client_clickhouse(dsn=url), client_close=lambda c: c.close()), lambda d: func_client_dict_close(clients=d, client_close=lambda c: c.close())),
        "client_mongodb": (lambda: func_client_mongodb(url=s.config_mongodb_url), lambda c: c.close()),
        "client_s3": (lambda: func_client_s3(region_name=s.config_aws_s3_region_name, **aws), lambda c: c._context.__aexit__(None, None, None)),
        "client_s3_resource": (lambda: func_client_s3_resource(region_name=s.config_aws_s3_region_name, **aws), lambda c: c.meta.client.close()),
        "client_sns": (lambda: func_client_sns(region_name=s.config_aws_sns_region_name, **aws), lambda c: func_client_sync_close(client=c)),
        "client_ses": (lambda: func_client_ses(region_name=s.config_aws_ses_region_name, **aws), lambda c: func_client_sync_close(client=c)),
        "client_openai": (lambda: func_client_openai(api_key=s.config_openai_key), lambda c: func_client_sync_close(client=c)),
        "client_gemini": (lambda: func_client_gemini(api_key=s.config_gemini_key), lambda c: func_client_sync_close(client=c)),
        "client_anthropic": (lambda: func_client_anthropic(api_key=s.config_anthropic_key), lambda c: c.close()),
        "client_celery_producer": (lambda: func_client_celery(url=s.config_celery_url), lambda c: func_client_sync_close(client=c)),
        "client_kafka_producer": (lambda: func_client_kafka(url=s.config_kafka_url, username=s.config_kafka_username, password=s.config_kafka_password), lambda c: c.stop()),
        "client_rabbitmq_producer": (rabbitmq_open, lambda c: func_rabbitmq_close(connection=rabbitmq.get("connection"), channel=c)),
        "client_sftp": (lambda: func_client_sftp(host=s.config_sftp_host, port=s.config_sftp_port, username=s.config_sftp_username, password=s.config_sftp_password, known_hosts_path=s.config_sftp_known_hosts_path, is_host_verify=s.config_sftp_is_host_verify), lambda c: func_sftp_close(client=c)),
        "client_azure_email": (lambda: func_client_azure_email(connection_string=s.config_azure_email_connection_string), lambda c: func_client_sync_close(client=c)),
        "client_azure_sms": (lambda: func_client_azure_sms(connection_string=s.config_azure_sms_connection_string), lambda c: func_client_sync_close(client=c)),
        "client_azure_blob": (lambda: func_client_azure_blob(account_name=s.config_azure_account_name, account_key=s.config_azure_account_key), lambda c: c.close()),
    }

def func_client_registry_build(*, app_state: State) -> dict:
    """Atom's registry plus the project's: the optional func_extend_client(*, app_state) in function_extend/ returns more entries in the same shape (name -> (open, close)). A project name must start with client_ and not be one of Atom's."""
    registry = func_client_registry(app_state=app_state)
    extend_client = getattr(app_state, "func_extend_client", None)
    if extend_client is None: return registry
    extend = extend_client(app_state=app_state)
    if not isinstance(extend, dict): raise Exception("func_extend_client must return a dict: name -> (open, close)")
    for name, entry in extend.items():
        if not isinstance(name, str) or not name.startswith("client_"): raise Exception(f"func_extend_client: {name!r} must start with client_")
        if name in registry: raise Exception(f"func_extend_client: {name} is Atom's client, choose another name")
        if not (isinstance(entry, tuple) and len(entry) == 2 and callable(entry[0]) and (entry[1] is None or callable(entry[1]))): raise Exception(f"func_extend_client: {name} must be (open, close), close may be None")
        registry[name] = entry
    return registry

async def func_client_open_one(*, client_open) -> object:
    """Call one open (sync or async) and return its client."""
    result = client_open()
    return await result if inspect.isawaitable(result) else result

async def func_client_registry_open(*, registry: dict) -> dict:
    """Open every client of the registry at once; returns name -> client (None when its settings are empty). When any fails, or startup is cancelled, the ones that opened are closed first; one failure raises its own error, several raise one error naming each."""
    names = list(registry)
    tasks = [asyncio.ensure_future(func_client_open_one(client_open=registry[name][0])) for name in names]
    try: await asyncio.gather(*tasks, return_exceptions=True)
    except BaseException:
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await func_client_close(registry=registry, clients={name: task.result() for name, task in zip(names, tasks, strict=True) if task.done() and not task.cancelled() and task.exception() is None})
        raise
    clients = {name: task.result() for name, task in zip(names, tasks, strict=True) if task.exception() is None}
    failed = [(name, task.exception()) for name, task in zip(names, tasks, strict=True) if task.exception() is not None]
    if not failed: return clients
    await func_client_close(registry=registry, clients=clients)
    if len(failed) == 1: raise failed[0][1]
    raise Exception("clients failed to open: " + "; ".join(f"{name}: {error}" for name, error in failed)) from failed[0][1]

async def func_client_close(*, registry: dict, clients: dict) -> None:
    """Close each client of clients (name -> client) with its registry close, the project's first (reverse registry order); a client that is None or has no close is skipped, and one failing to close is printed while the rest still close."""
    for name in reversed(list(registry)):
        client, close = clients.get(name), registry[name][1]
        if client is None or close is None: continue
        try:
            result = close(client)
            if inspect.isawaitable(result): await result
        except Exception as e: print(f"❌ close {name}: {e}")
