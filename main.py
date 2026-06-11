# packages
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
import httpx
import motor.motor_asyncio
import openai
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

# function
from function import *
if importlib.util.find_spec("function_extend"): from function_extend import *

# config
from config import *
if importlib.util.find_spec("config_extend"): from config_extend import *

# schema
if importlib.util.find_spec("schema"): from schema import *

# lifespan
@asynccontextmanager
async def func_lifespan(app:"FastAPI"):
    try:
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
        client_postgres_pool = await asyncpg.create_pool(dsn=app.state.config_postgres_url, min_size=5, max_size=20) if app.state.config_postgres_url else None
        client_postgres_pool_read = await asyncpg.create_pool(dsn=app.state.config_postgres_url_read, min_size=5, max_size=20) if app.state.config_postgres_url_read else None
        client_redis = redis.Redis.from_pool(redis.ConnectionPool.from_url(app.state.config_redis_url)) if app.state.config_redis_url else None
        client_redis_producer = redis.Redis.from_pool(redis.ConnectionPool.from_url(app.state.config_redis_url_queue)) if app.state.config_redis_url_queue else None
        client_mongodb = motor.motor_asyncio.AsyncIOMotorClient(app.state.config_mongodb_url) if app.state.config_mongodb_url else None
        client_mssql = await aioodbc.create_pool(dsn=app.state.config_mssql_url, pool_recycle=60) if app.state.config_mssql_url else None
        client_mssql_read = await aioodbc.create_pool(dsn=app.state.config_mssql_url_read, pool_recycle=60) if app.state.config_mssql_url_read else None
        client_s3 = aiobotocore.session.get_session().create_client("s3", region_name=app.state.config_aws_s3_region_name, aws_access_key_id=app.state.config_aws_access_key_id, aws_secret_access_key=app.state.config_aws_secret_access_key) if app.state.config_aws_s3_region_name else None
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
        # postges schema init
        if client_postgres_pool and app.state.config_is_enable_postgres_schema_init: await app.state.func_postgres_schema_init(client_postgres_pool=client_postgres_pool, config_postgres=app.state.config_postgres)
        # cache init
        cache_postgres_schema = await app.state.func_postgres_schema_read(client_postgres_pool=client_postgres_pool) if client_postgres_pool else {}
        cache_config = await app.state.func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=app.state.config_sql.get("config"), is_json_value=1) if client_postgres_pool and "config" in cache_postgres_schema else {}
        cache_postgres_table_list = list(cache_postgres_schema.keys())
        cache_postgres_column_list = sorted(list(set(col for table in cache_postgres_schema.values() for col in table.keys())))
        app.state.cache_postgres_schema = cache_postgres_schema
        app.state.cache_postgres_table_list = cache_postgres_table_list
        app.state.cache_postgres_column_list = cache_postgres_column_list
        cache_openapi=app.state.func_openapi_spec_generate(app_routes=app.routes, app_state=app.state)
        cache_users_role = await app.state.func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=app.state.config_sql.get("users_role")) if client_postgres_pool else {}
        cache_users_deactivated = await app.state.func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=app.state.config_sql.get("users_deactivated")) if client_postgres_pool else {}
        cache_users_deleted = await app.state.func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=app.state.config_sql.get("users_deleted")) if client_postgres_pool else {}
        cache_ratelimiter, cache_api_response, cache_postgres_buffer_create = {}, {}, {}
        # flush lock
        app.state.flush_lock, app.state.pulse_flush_task = asyncio.Lock(), None
        # app state add
        [setattr(app.state, k, v) for k, v in {**globals(), **locals()}.items() if k.startswith(("client_", "cache_"))]
        # postgres buffer flush loop
        async def pulse_flush():
            buffer_flush_interval_sec = 60
            while True:
                try:
                    await asyncio.sleep(buffer_flush_interval_sec)
                    if client_postgres_pool:
                        async with app.state.flush_lock:
                            await app.state.func_postgres_create(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=app.state.func_postgres_serialize, func_regex_check=app.state.func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=app.state.config_regex, buffer_limit=app.state.config_buffer_limit_default, mode="flush", table="", obj_list=[])
                except asyncio.CancelledError: break
                except Exception as e: print(f"❌ pulse flush error: {e}")
        app.state.pulse_flush_task = asyncio.create_task(pulse_flush())
    except Exception as e:
        print(f"❌ startup error: {e}")
        raise
    # shutdown
    yield
    try:
        # background task stop
        if app.state.pulse_flush_task:
            app.state.pulse_flush_task.cancel()
            try: await app.state.pulse_flush_task
            except asyncio.CancelledError: pass
        # postgres buffer flush final
        if client_postgres_pool:
            async with app.state.flush_lock:
                await app.state.func_postgres_create(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=app.state.func_postgres_serialize, func_regex_check=app.state.func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=app.state.config_regex, buffer_limit=app.state.config_buffer_limit_default, mode="flush", table="", obj_list=[])
        # client disconnect
        if client_http: await client_http.aclose()
        if client_postgres_pool: await client_postgres_pool.close()
        if client_postgres_pool_read: await client_postgres_pool_read.close()
        if client_redis: await client_redis.aclose()
        if client_mongodb: client_mongodb.close()
        if client_mssql: client_mssql.close(); await client_mssql.wait_closed()
        if client_mssql_read: client_mssql_read.close(); await client_mssql_read.wait_closed()
        if client_posthog: client_posthog.shutdown(); client_posthog.flush()
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
app = FastAPI(debug=True, lifespan=func_lifespan, openapi_url=None, docs_url=None, redoc_url=None)

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
    if request.method == "OPTIONS": return await api_function(request)
    start, error, response_type, request.state.user = time.perf_counter(), None, 1, {}
    app_state = request.app.state
    try:
        request.state.user = await app_state.func_middleware_check_auth(headers=request.headers, url_path=request.url.path, config_token_secret_key=app_state.config_token_secret_key)
        await app_state.func_middleware_check_user_role(user_dict=request.state.user, url_path=request.url.path, config_api=app_state.config_api, client_postgres_pool=app_state.client_postgres_pool, client_redis=app_state.client_redis, cache_users_role=app_state.cache_users_role, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_middleware_check_user_deactivated(user_dict=request.state.user, url_path=request.url.path, config_api=app_state.config_api, client_postgres_pool=app_state.client_postgres_pool, client_redis=app_state.client_redis, cache_users_deactivated=app_state.cache_users_deactivated, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_middleware_check_user_deleted(user_dict=request.state.user, url_path=request.url.path, config_api=app_state.config_api, client_postgres_pool=app_state.client_postgres_pool, client_redis=app_state.client_redis, cache_users_deleted=app_state.cache_users_deleted, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_middleware_check_ratelimiter(client_redis=app_state.client_redis, config_api=app_state.config_api, url_path=request.url.path, identifier=request.state.user.get("id") if request.state.user else request.client.host, cache_ratelimiter=app_state.cache_ratelimiter)
        user_id, path, query_params = (request.state.user.get("id") if request.state.user else 0), request.url.path, dict(request.query_params)
        response = await app_state.func_middleware_api_cache(mode="get", path=path, query_params=query_params, config_api=app_state.config_api, client_redis=app_state.client_redis, user_id=user_id, cache_api_response=app_state.cache_api_response)
        if not response:
            if query_params.get("is_background") == "1":
                response_type = 4
                response = await app_state.func_middleware_api_background(scope=request.scope, body_bytes=await request.body(), api_function=api_function)
            else:
                response = await api_function(request)
                response = await app_state.func_middleware_api_cache(mode="set", path=path, query_params=query_params, response=response, config_api=app_state.config_api, client_redis=app_state.client_redis, user_id=user_id, cache_api_response=app_state.cache_api_response)
                if getattr(response, "is_cache_set", False): response_type = 2
        else:
            response_type = 3
    except Exception as e:
        response_type = 5
        error, response = await app_state.func_middleware_api_response_error(exception=e, is_traceback=1, sentry_dsn=app_state.config_sentry_dsn)
    if pool := app_state.client_postgres_pool:
        with suppress(Exception): await app_state.func_postgres_create(client_postgres_pool=pool, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get("log_api", {}).get("buffer_limit", app_state.config_buffer_limit_default), mode="buffer", table="log_api", obj_list=[{"created_by_id": request.state.user.get("id") if getattr(request.state, "user", None) else None, "response_type": response_type, "ip_address": request.client.host if request.client else None, "path": request.url.path, "method": request.method, "query_param": str(request.query_params), "status_code": response.status_code if hasattr(response, "status_code") else None, "response_time_ms": int((time.perf_counter() - start) * 1000), "error": error}])
    return response

# cors
app.add_middleware(CORSMiddleware, allow_origins=[], allow_origin_regex=".*", allow_methods=["*"], allow_headers=["*"], expose_headers=["*"], allow_credentials=True)

# main
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
