# import packages
import asyncio
import importlib.util
import os
import shutil
import time
from contextlib import asynccontextmanager, suppress
import aio_pika
import aiobotocore.session
import aioodbc
import asyncpg
import asyncssh
import boto3
import clickhouse_connect
import httpx
import motor.motor_asyncio
import openai
import pyodbc
import redis.asyncio as redis
import sentry_sdk
import uvicorn
from aiokafka import AIOKafkaProducer
from argon2 import PasswordHasher
from azure.communication.email import EmailClient
from azure.storage.blob.aio import BlobServiceClient
from celery import Celery
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
from posthog import Posthog
from sentry_sdk.integrations.fastapi import FastApiIntegration

# import custom files
from function import *
from config import *

#import extend files
if importlib.util.find_spec("function_extend"): from function_extend import *
if importlib.util.find_spec("config_extend"): from config_extend import *

# lifespan
@asynccontextmanager
async def func_lifespan(app:"FastAPI"):
    try:
        app.state.runtime_background_tasks = set()
        app.state.postgres_buffer_flush_task = None
        app.state.inmemory_cache_cleanup_task = None
        # start
        start_journey = time.perf_counter()
        # check
        app.state.func_check(app=app)
        # structure
        if os.path.isdir("tmp") and not os.path.islink("tmp"): shutil.rmtree("tmp")
        elif os.path.exists("tmp"): os.remove("tmp")
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("secret", exist_ok=True)
        # client init
        client_password_hasher = PasswordHasher()
        client_http = httpx.AsyncClient()
        postgres_pool_kwargs = {"min_size": app.state.config_postgres_pool_min_size, "max_size": app.state.config_postgres_pool_max_size}
        if app.state.config_is_read_only: postgres_pool_kwargs["server_settings"] = {"default_transaction_read_only": "on"}
        client_postgres = await asyncpg.create_pool(dsn=app.state.config_postgres_url, **postgres_pool_kwargs) if app.state.config_postgres_url else None
        client_postgres_dict = {name: await asyncpg.create_pool(dsn=url, **postgres_pool_kwargs) for name, url in (app.state.config_postgres_url_dict or {}).items() if url}
        client_redis = redis.Redis.from_pool(redis.ConnectionPool.from_url(app.state.config_redis_url)) if app.state.config_redis_url else None
        client_redis_ratelimiter = redis.Redis.from_pool(redis.ConnectionPool.from_url(app.state.config_redis_url_ratelimiter)) if app.state.config_redis_url_ratelimiter else None
        client_redis_producer = redis.Redis.from_pool(redis.ConnectionPool.from_url(app.state.config_redis_url_queue)) if app.state.config_redis_url_queue else None
        client_mongodb = motor.motor_asyncio.AsyncIOMotorClient(app.state.config_mongodb_url) if app.state.config_mongodb_url else None
        pyodbc.pooling = False  # must be off before the first connect: driver-manager pooling hands cached (possibly dead) sockets back to pool_recycle's close/reconnect, making the recycle a no-op
        client_mssql = await aioodbc.create_pool(dsn=app.state.config_mssql_url, minsize=1, maxsize=10, pool_recycle=60) if app.state.config_mssql_url else None
        client_clickhouse = await clickhouse_connect.get_async_client(dsn=app.state.config_clickhouse_url) if app.state.config_clickhouse_url else None
        client_s3_context = aiobotocore.session.get_session().create_client("s3", region_name=app.state.config_aws_s3_region_name, aws_access_key_id=app.state.config_aws_access_key_id, aws_secret_access_key=app.state.config_aws_secret_access_key) if app.state.config_aws_s3_region_name else None
        client_s3 = await client_s3_context.__aenter__() if client_s3_context else None
        client_s3_resource = boto3.resource("s3", region_name=app.state.config_aws_s3_region_name, aws_access_key_id=app.state.config_aws_access_key_id, aws_secret_access_key=app.state.config_aws_secret_access_key) if app.state.config_aws_s3_region_name else None
        client_sns = boto3.client("sns", region_name=app.state.config_aws_sns_region_name, aws_access_key_id=app.state.config_aws_access_key_id, aws_secret_access_key=app.state.config_aws_secret_access_key) if app.state.config_aws_sns_region_name else None
        client_ses = boto3.client("ses", region_name=app.state.config_aws_ses_region_name, aws_access_key_id=app.state.config_aws_access_key_id, aws_secret_access_key=app.state.config_aws_secret_access_key) if app.state.config_aws_ses_region_name else None
        client_openai = openai.OpenAI(api_key=app.state.config_openai_key) if app.state.config_openai_key else None
        client_gemini = genai.Client(api_key=app.state.config_gemini_key) if app.state.config_gemini_key else None
        client_posthog = Posthog(app.state.config_posthog_project_key, host=app.state.config_posthog_project_host) if app.state.config_posthog_project_key else None
        client_celery_producer = Celery("atom", broker=app.state.config_celery_url, backend=app.state.config_celery_url) if app.state.config_celery_url else None
        client_kafka_producer = (AIOKafkaProducer(bootstrap_servers=app.state.config_kafka_url, security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=app.state.config_kafka_username, sasl_plain_password=app.state.config_kafka_password) if app.state.config_kafka_username else AIOKafkaProducer(bootstrap_servers=app.state.config_kafka_url)) if app.state.config_kafka_url else None; await client_kafka_producer.start() if client_kafka_producer else None
        client_rabbitmq = await aio_pika.connect_robust(app.state.config_rabbitmq_url) if app.state.config_rabbitmq_url else None; client_rabbitmq_producer = await client_rabbitmq.channel() if client_rabbitmq else None
        client_sftp = await asyncssh.connect(host=app.state.config_sftp_host, port=int(app.state.config_sftp_port), username=app.state.config_sftp_username, password=app.state.config_sftp_password, known_hosts=None) if app.state.config_sftp_host else None
        client_azure_email = EmailClient.from_connection_string(app.state.config_azure_email_connection_string) if app.state.config_azure_email_connection_string else None
        client_azure_blob = BlobServiceClient.from_connection_string(f"DefaultEndpointsProtocol=https;AccountName={app.state.config_azure_account_name};AccountKey={app.state.config_azure_account_key};EndpointSuffix=core.windows.net") if (app.state.config_azure_account_name and app.state.config_azure_account_key) else None
        # client helper
        if app.state.config_log_db is not None and app.state.config_log_db not in client_postgres_dict: raise Exception(f"config_log_db '{app.state.config_log_db}' not found in config_postgres_url_dict")
        client_postgres_log = client_postgres if app.state.config_log_db is None else client_postgres_dict[app.state.config_log_db]
        # postges schema init
        if client_postgres and not app.state.config_is_read_only and app.state.config_is_enable_postgres_schema_init: await app.state.func_postgres_schema_init(client_postgres=client_postgres, config_postgres=app.state.config_postgres, root_user_password_hash=client_password_hasher.hash(config_root_user_password) if config_root_user_password else None)
        # cache schema init
        cache_postgres_schema = await app.state.func_postgres_schema_read(client_postgres=client_postgres) if client_postgres else {}
        cache_postgres_schema_ai = await app.state.func_postgres_schema_read_ai(client_postgres=client_postgres) if client_postgres else {}
        cache_postgres_schema_dict = {name: await app.state.func_postgres_schema_read(client_postgres=client) for name, client in client_postgres_dict.items()}
        cache_postgres_schema_ai_dict = {name: await app.state.func_postgres_schema_read_ai(client_postgres=client) for name, client in client_postgres_dict.items()}
        cache_postgres_schema_table_list = list(cache_postgres_schema.keys())
        cache_postgres_schema_column_list = sorted(list(set(col for table in cache_postgres_schema.values() for col in table.keys())))
        #cache db names
        cache_postgres_db_name_list = list(client_postgres_dict)
        # cache data init
        cache_config = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("config"), is_json_value=1) if client_postgres and "config" in cache_postgres_schema else {}
        cache_users_role = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("users_role")) if client_postgres else {}
        cache_users_deactivated = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("users_deactivated")) if client_postgres else {}
        cache_users_deleted = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("users_deleted")) if client_postgres else {}
        # caches in-memory
        cache_api_response = {}
        cache_ratelimiter = {}
        cache_postgres_buffer_create = {}
        cache_postgres_buffer_log_api = {}
        # app state add
        [setattr(app.state, k, v) for k, v in {**globals(), **locals()}.items() if k.startswith(("client_", "cache_"))]
        # openapi spec generation
        app.state.cache_openapi = app.state.func_openapi_spec_generate(app_routes=app.routes, app_state=app.state)
        # start periodic tasks
        app.state.postgres_buffer_flush_lock = asyncio.Lock()
        if not app.state.config_is_read_only: app.state.postgres_buffer_flush_task = asyncio.create_task(app.state.func_postgres_buffers_flush_periodic(app_state=app.state, client_postgres=client_postgres, cache_postgres_buffer_create=cache_postgres_buffer_create, client_postgres_log=client_postgres_log, cache_postgres_buffer_log_api=cache_postgres_buffer_log_api, interval_sec=60))
        app.state.inmemory_cache_cleanup_task = asyncio.create_task(app.state.func_inmemory_cache_cleanup_periodic(cache_api_response=cache_api_response, cache_ratelimiter=cache_ratelimiter, interval_sec=300))
    except Exception as e:
        print(f"❌ startup error: {e}")
        raise
    # shutdown
    yield
    try:
        # stop runtime background tasks
        runtime_background_tasks = getattr(app.state, "runtime_background_tasks", set())
        if runtime_background_tasks:
            await app.state.func_async_tasks_cancel(task_list=list(runtime_background_tasks), timeout_sec=5)
        # stop periodic tasks
        postgres_buffer_flush_task = getattr(app.state, "postgres_buffer_flush_task", None)
        if postgres_buffer_flush_task: await app.state.func_async_tasks_cancel(task_list=[postgres_buffer_flush_task], timeout_sec=5)
        inmemory_cache_cleanup_task = getattr(app.state, "inmemory_cache_cleanup_task", None)
        if inmemory_cache_cleanup_task: await app.state.func_async_tasks_cancel(task_list=[inmemory_cache_cleanup_task], timeout_sec=5)
        # postgres buffer flush final
        if not app.state.config_is_read_only:
            try:
                await app.state.func_postgres_buffer_flush(app_state=app.state, client_postgres=client_postgres, cache_postgres_buffer=cache_postgres_buffer_create)
            except Exception as e: print(f"❌ final primary buffer flush error: {e}")
            try:
                await app.state.func_postgres_buffer_flush(app_state=app.state, client_postgres=client_postgres_log, cache_postgres_buffer=cache_postgres_buffer_log_api)
            except Exception as e: print(f"❌ final log api buffer flush error: {e}")
        # client disconnect
        if client_http: await client_http.aclose()
        if client_postgres: await client_postgres.close()
        for client_postgres_item in client_postgres_dict.values(): await client_postgres_item.close()
        if client_redis: await client_redis.aclose()
        if client_redis_ratelimiter: await client_redis_ratelimiter.aclose()
        if client_mongodb: client_mongodb.close()
        if client_mssql: client_mssql.close(); await client_mssql.wait_closed()
        if client_clickhouse: await client_clickhouse.close()
        if client_s3_context: await client_s3_context.__aexit__(None, None, None)
        if client_s3_resource and hasattr(client_s3_resource.meta.client, "close"): client_s3_resource.meta.client.close()
        if client_sns and hasattr(client_sns, "close"): client_sns.close()
        if client_ses and hasattr(client_ses, "close"): client_ses.close()
        if client_openai and hasattr(client_openai, "close"): client_openai.close()
        if client_gemini and hasattr(client_gemini, "close"): client_gemini.close()
        if client_posthog: client_posthog.shutdown(); client_posthog.flush()
        if client_celery_producer and hasattr(client_celery_producer, "close"): client_celery_producer.close()
        if client_kafka_producer: await client_kafka_producer.stop()
        if client_rabbitmq_producer and not client_rabbitmq_producer.is_closed: await client_rabbitmq_producer.close()
        if client_rabbitmq and not client_rabbitmq.is_closed: await client_rabbitmq.close()
        if client_redis_producer: await client_redis_producer.aclose()
        if client_sftp: client_sftp.close(); await client_sftp.wait_closed()
        if client_azure_email and hasattr(client_azure_email, "close"): client_azure_email.close()
        if client_azure_blob: await client_azure_blob.close()
    except Exception as e:
        print(f"❌ shutdown error: {e}")

# app
app = FastAPI(debug=bool(config_is_debug), lifespan=func_lifespan, openapi_url=None, docs_url=None, redoc_url=None)

# state
[setattr(app.state, k, v) for k, v in globals().items() if k.startswith(("func_", "config_"))]

# router
func_app_router_add(app=app, router_dir=os.path.join(os.path.dirname(__file__), "router"), router_order={"index": 0, "auth": 1, "my": 2, "public": 3, "private": 4, "admin": 5})

# static
app.mount("/static", StaticFiles(directory="./static", check_dir=False), name="static")

# sentry
if config_sentry_dsn: sentry_sdk.init(dsn=config_sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=False)

# middleware
@app.middleware("http")
async def middleware(request, api_function):
    #request init
    if request.method == "OPTIONS": return await api_function(request)
    start, error, response_type, request.state.user = time.perf_counter(), None, "direct_no_cache_set", {}
    app_state = request.app.state
    try:
        # route config
        route = request.scope.get("route")
        path = request.url.path
        route_path = getattr(route, "path", None) or path
        api_cfg = app_state.config_api.get(route_path, {})
        is_token_check = api_cfg.get("is_token_check", 0)
        user_check_role = api_cfg.get("user_check_role")
        user_check_deactivated = api_cfg.get("user_check_deactivated")
        user_check_deleted = api_cfg.get("user_check_deleted")
        rate_limit = api_cfg.get("rate_limit")
        cache = api_cfg.get("cache")
        # authentication
        request.state.user = await app_state.func_token_decode(headers=request.headers, config_token_secret_key=app_state.config_token_secret_key)
        await app_state.func_middleware_check_token(user_dict=request.state.user, url_path=path, is_token_check=is_token_check, user_check_role=user_check_role, user_check_deactivated=user_check_deactivated, user_check_deleted=user_check_deleted)
        # authorization
        await app_state.func_middleware_check_role(user_dict=request.state.user, user_check_role=user_check_role, client_postgres=app_state.client_postgres, client_redis=app_state.client_redis, cache_users_role=app_state.cache_users_role, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_middleware_check_user_deactivated(user_dict=request.state.user, user_check_deactivated=user_check_deactivated, client_postgres=app_state.client_postgres, client_redis=app_state.client_redis, cache_users_deactivated=app_state.cache_users_deactivated, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_middleware_check_user_deleted(user_dict=request.state.user, user_check_deleted=user_check_deleted, client_postgres=app_state.client_postgres, client_redis=app_state.client_redis, cache_users_deleted=app_state.cache_users_deleted, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        # rate limiting
        await app_state.func_middleware_check_ratelimiter(client_redis=app_state.client_redis_ratelimiter, rate_limit=rate_limit, url_path=path, identifier=request.state.user.get("id") if request.state.user else request.client.host, cache_ratelimiter=app_state.cache_ratelimiter)
        # api cache
        user_id, query_params = (request.state.user.get("id") if request.state.user else 0), dict(request.query_params)
        response = await app_state.func_middleware_api_cache(mode="get", path=path, query_params=query_params, cache=cache, client_redis=app_state.client_redis, user_id=user_id, cache_api_response=app_state.cache_api_response)
        # api execution
        if not response:
            if query_params.get("is_background") == "1":
                response_type = "background_added"
                response = await app_state.func_middleware_api_background(scope=request.scope, body_bytes=await request.body(), api_function=api_function)
            else:
                response = await api_function(request)
                response = await app_state.func_middleware_api_cache(mode="set", path=path, query_params=query_params, response=response, cache=cache, client_redis=app_state.client_redis, user_id=user_id, cache_api_response=app_state.cache_api_response)
                if getattr(response, "is_cache_set", False): response_type = "direct_cache_set"
        else:
            response_type = "cache_response"
    # error response
    except Exception as e:
        response_type = "error"
        error, response = await app_state.func_middleware_api_response_error(exception=e, is_traceback=1, sentry_dsn=app_state.config_sentry_dsn)
    # api log buffer
    if not app_state.config_is_read_only and app_state.client_postgres_log:
        with suppress(Exception): await app_state.func_postgres_create(client_postgres=app_state.client_postgres_log, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_log_api, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get("log_api", {}).get("buffer_limit", app_state.config_buffer_limit_default), mode="buffer", table="log_api", obj_list=[{"created_by_id": request.state.user.get("id") if getattr(request.state, "user", None) else None, "response_type": response_type, "ip_address": request.client.host if request.client else None, "path": request.url.path, "method": request.method, "query_param": str(request.query_params), "status_code": response.status_code if hasattr(response, "status_code") else None, "response_time_ms": int((time.perf_counter() - start) * 1000), "error": error}])
    return response

# cors
app.add_middleware(CORSMiddleware, allow_origins=config_cors_allow_origins, allow_origin_regex=config_cors_allow_origin_regex, allow_methods=config_cors_allow_methods, allow_headers=config_cors_allow_headers, expose_headers=config_cors_expose_headers, allow_credentials=config_cors_allow_credentials)

# main
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
