#import
from .config import *
from .function import *
import asyncio

#lifespan
from contextlib import asynccontextmanager
@asynccontextmanager
async def func_lifespan(app:"FastAPI"):
   try:
       #start
       import time
       start_journey = time.perf_counter()
       #structure
       import os
       for directory in ("tmp", "secret"):os.makedirs(directory, exist_ok=True)
       #client init
       import aio_pika, aiobotocore.session, asyncpg, asyncssh, boto3, httpx, motor.motor_asyncio, openai
       import redis.asyncio as redis
       from google import genai
       from argon2 import PasswordHasher
       from aiokafka import AIOKafkaProducer
       from azure.storage.blob.aio import BlobServiceClient
       from celery import Celery
       from posthog import Posthog
       client_password_hasher = PasswordHasher()
       client_http = httpx.AsyncClient()
       client_postgres_pool = await asyncpg.create_pool(dsn=getattr(app.state, "config_postgres_url", config_postgres_url), min_size=config_postgres_min_connection, max_size=config_postgres_max_connection) if getattr(app.state, "config_postgres_url", config_postgres_url) else None
       client_redis = redis.Redis.from_pool(redis.ConnectionPool.from_url(getattr(app.state, "config_redis_url", config_redis_url))) if (getattr(app.state, "config_redis_url", None) or config_redis_url) else None
       client_redis_producer = redis.Redis.from_pool(redis.ConnectionPool.from_url(getattr(app.state, "config_redis_queue_url", config_redis_queue_url))) if getattr(app.state, "config_redis_queue_url", config_redis_queue_url) else None
       client_mongodb = motor.motor_asyncio.AsyncIOMotorClient(getattr(app.state, "config_mongodb_url", config_mongodb_url)) if getattr(app.state, "config_mongodb_url", config_mongodb_url) else None
       client_s3 = aiobotocore.session.get_session().create_client("s3", region_name=getattr(app.state, "config_s3_region_name", config_s3_region_name), aws_access_key_id=getattr(app.state, "config_aws_access_key_id", config_aws_access_key_id), aws_secret_access_key=getattr(app.state, "config_aws_secret_access_key", config_aws_secret_access_key)) if config_s3_region_name else None
       client_s3_resource = boto3.resource("s3", region_name=getattr(app.state, "config_s3_region_name", config_s3_region_name), aws_access_key_id=getattr(app.state, "config_aws_access_key_id", config_aws_access_key_id), aws_secret_access_key=getattr(app.state, "config_aws_secret_access_key", config_aws_secret_access_key)) if config_s3_region_name else None
       client_sns = boto3.client("sns", region_name=getattr(app.state, "config_sns_region_name", config_sns_region_name), aws_access_key_id=getattr(app.state, "config_aws_access_key_id", config_aws_access_key_id), aws_secret_access_key=getattr(app.state, "config_aws_secret_access_key", config_aws_secret_access_key)) if config_sns_region_name else None
       client_ses = boto3.client("ses", region_name=getattr(app.state, "config_ses_region_name", config_ses_region_name), aws_access_key_id=getattr(app.state, "config_aws_access_key_id", config_aws_access_key_id), aws_secret_access_key=getattr(app.state, "config_aws_secret_access_key", config_aws_secret_access_key)) if config_ses_region_name else None
       client_openai = openai.OpenAI(api_key=getattr(app.state, "config_openai_key", config_openai_key)) if getattr(app.state, "config_openai_key", config_openai_key) else None
       client_gemini = genai.Client(api_key=config_gemini_key) if config_gemini_key else None
       client_posthog = Posthog(config_posthog_project_key, host=config_posthog_project_host) if config_posthog_project_key else None
       client_celery_producer = Celery("atom", broker=config_celery_url, backend=config_celery_url) if config_celery_url else None
       client_kafka_producer = (AIOKafkaProducer(bootstrap_servers=config_kafka_url, security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaProducer(bootstrap_servers=config_kafka_url)) if config_kafka_url else None; await client_kafka_producer.start() if client_kafka_producer else None
       client_rabbitmq = await aio_pika.connect_robust(config_rabbitmq_url) if config_rabbitmq_url else None; client_rabbitmq_producer = await client_rabbitmq.channel() if client_rabbitmq else None
       client_sftp = await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, password=config_sftp_password, known_hosts=None) if config_sftp_host else None
       client_azure_blob = BlobServiceClient.from_connection_string(f"DefaultEndpointsProtocol=https;AccountName={config_azure_account_name};AccountKey={config_azure_account_key};EndpointSuffix=core.windows.net") if (config_azure_account_name and config_azure_account_key) else None
       #postges schema init
       if client_postgres_pool and getattr(app.state, "config_is_enable_postgres_init_startup", config_is_enable_postgres_init_startup) == 1: await func_postgres_schema_init(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, config_postgres=getattr(app.state, "config_postgres", config_postgres), config_root_user_password=getattr(app.state, "config_root_user_password", config_root_user_password))
       #cache init
       cache_postgres_schema = await func_postgres_schema_read(client_postgres_pool=client_postgres_pool) if client_postgres_pool else {}
       cache_postgres_table_list = list(cache_postgres_schema.keys())
       cache_postgres_column_list = sorted(list(set(col for table in cache_postgres_schema.values() for col in table.keys())))
       cache_users_role = await func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=config_sql.get("users_role")) if client_postgres_pool else {}
       cache_users_is_active = await func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=config_sql.get("users_is_active")) if client_postgres_pool else {}
       cache_ratelimiter, cache_api_response, cache_postgres_buffer_create = {}, {}, {}
       app.state.flush_lock = asyncio.Lock()
       #app state add
       [setattr(app.state, k, v) for k, v in {**globals(), **locals()}.items() if k.startswith(("client_", "cache_", "config_", "func_"))]
       #openapi spec
       app.state.cache_openapi=func_openapi_spec_generate(app_routes=app.routes, config_api_roles_auth=config_api_roles_auth, app_state=app.state)
       #postgres buffer flush loop
       async def pulse_flush():
          while True:
             try:
                await asyncio.sleep(config_buffer_flush_interval_sec)
                if client_postgres_pool:
                    async with app.state.flush_lock:
                        await func_postgres_create(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=config_regex, config_table=config_table, config_obj_list_limit=0, config_buffer_limit=config_buffer_limit, mode="flush", table="", obj_list=[], is_serialize=0)
             except asyncio.CancelledError: break
             except Exception as e: print(f"❌ pulse flush error: {e}")
       if getattr(app.state, "config_is_enable_background_workers", 1) == 1:
            app.state.pulse_flush_task = asyncio.create_task(pulse_flush())
   except Exception as e:
       print(f"❌ startup error: {e}")
       raise
   yield
   try:
       #background task stop
       if getattr(app.state, "pulse_flush_task", None):
           app.state.pulse_flush_task.cancel()
           try: await app.state.pulse_flush_task
           except asyncio.CancelledError: pass
       #postgres buffer flush final
       if client_postgres_pool:
          async with app.state.flush_lock:
              await func_postgres_create(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=config_regex, config_table=config_table, config_obj_list_limit=config_obj_list_limit, config_buffer_limit=config_buffer_limit, mode="flush", table="", obj_list=[], is_serialize=0)
       #client disconnect
       if client_http: await client_http.aclose()
       if client_postgres_pool: await client_postgres_pool.close()
       if client_redis: await client_redis.aclose()
       if client_mongodb: client_mongodb.close()
       if client_posthog: client_posthog.shutdown(); client_posthog.flush()
       if client_kafka_producer: await client_kafka_producer.stop()
       if client_rabbitmq_producer and not client_rabbitmq_producer.is_closed: await client_rabbitmq_producer.close()
       if client_rabbitmq and not client_rabbitmq.is_closed: await client_rabbitmq.close()
       if client_redis_producer: await client_redis_producer.aclose()
       if client_sftp: client_sftp.close(); await client_sftp.wait_closed()
       if client_azure_blob: await client_azure_blob.close()
   except Exception as e:
       print(f"❌ shutdown error: {e}")

#app
from fastapi import FastAPI
app = FastAPI(debug=True, lifespan=func_lifespan, openapi_url=None, docs_url=None, redoc_url=None)

#state pre-population (ensures func_* are available even before lifespan)
[setattr(app.state, k, v) for k, v in globals().items() if k.startswith(("func_", "config_"))]

#router
import os
func_app_router_add(app=app, router_dir=os.path.join(os.path.dirname(__file__), "router"), router_order={"index": 0, "auth": 1, "my": 2, "public": 3, "private": 4, "admin": 5})

#static
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="./static", check_dir=False), name="static")

#sentry
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
if config_sentry_dsn: sentry_sdk.init(dsn=config_sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=True)

#middleware
@app.middleware("http")
async def middleware(request, api_function):
    import time
    if request.method == "OPTIONS": return await api_function(request)
    start, error, request.state.user = time.perf_counter(), None, {}
    app_state = request.app.state
    try:
        request.state.user = await getattr(app_state, "func_middleware_check_auth", func_middleware_check_auth)(headers=request.headers, url_path=request.url.path, config_token_secret_key=getattr(app_state, "config_token_secret_key", config_token_secret_key), config_api_roles_auth=getattr(app_state, "config_api_roles_auth", config_api_roles_auth))
        await getattr(app_state, "func_middleware_check_role", func_middleware_check_role)(user_dict=request.state.user, url_path=request.url.path, config_api=getattr(app_state, "config_api", config_api), client_postgres_pool=getattr(app_state, "client_postgres_pool", None), client_redis=getattr(app_state, "client_redis", None), cache_users_role=getattr(app_state, "cache_users_role", {}), config_redis_cache_ttl_sec=getattr(app_state, "config_redis_cache_ttl_sec", config_redis_cache_ttl_sec))
        await getattr(app_state, "func_middleware_check_is_active", func_middleware_check_is_active)(user_dict=request.state.user, url_path=request.url.path, config_api=getattr(app_state, "config_api", config_api), client_postgres_pool=getattr(app_state, "client_postgres_pool", None), client_redis=getattr(app_state, "client_redis", None), cache_users_is_active=getattr(app_state, "cache_users_is_active", {}), config_redis_cache_ttl_sec=getattr(app_state, "config_redis_cache_ttl_sec", config_redis_cache_ttl_sec))
        await getattr(app_state, "func_middleware_check_ratelimiter", func_middleware_check_ratelimiter)(client_redis=getattr(app_state, "client_redis", None), config_api=getattr(app_state, "config_api", config_api), url_path=request.url.path, identifier=request.state.user.get("id") if request.state.user else request.client.host, cache_ratelimiter=getattr(app_state, "cache_ratelimiter", {}))
        response = await getattr(app_state, "func_middleware_api_response", func_middleware_api_response)(request=request, api_function=api_function, config_api=getattr(app_state, "config_api", config_api), client_redis=getattr(app_state, "client_redis", None), user_id=request.state.user.get("id") if request.state.user else 0, cache_api_response=getattr(app_state, "cache_api_response", {}))
    except Exception as e:
        error, response = await getattr(app_state, "func_middleware_api_response_error", func_middleware_api_response_error)(exception=e, is_traceback=getattr(app_state, "config_is_enable_traceback", config_is_enable_traceback), sentry_dsn=getattr(app_state, "config_sentry_dsn", config_sentry_dsn))
    from contextlib import suppress
    with suppress(Exception): await getattr(app_state, "func_middleware_api_log_create", func_middleware_api_log_create)(config_is_enable_log_api=getattr(app_state, "config_is_enable_log_api", config_is_enable_log_api), api_id=getattr(app_state, "config_api", {}).get(request.url.path, {}).get("id"), request=request, response=response, time_ms=int((time.perf_counter() - start) * 1000), user_id=request.state.user.get("id") if getattr(request.state, "user", None) else None, description=error, func_postgres_create=getattr(app_state, "func_postgres_create", func_postgres_create), client_postgres_pool=getattr(app_state, "client_postgres_pool", None), client_password_hasher=getattr(app_state, "client_password_hasher", None), func_postgres_serialize=getattr(app_state, "func_postgres_serialize", func_postgres_serialize), func_regex_check=getattr(app_state, "func_regex_check", func_regex_check), cache_postgres_schema=getattr(app_state, "cache_postgres_schema", {}), cache_postgres_buffer_create=getattr(app_state, "cache_postgres_buffer_create", {}), config_regex=getattr(app_state, "config_regex", config_regex), config_table=getattr(app_state, "config_table", config_table), config_obj_list_limit=getattr(app_state, "config_obj_list_limit", config_obj_list_limit), config_buffer_limit=getattr(app_state, "config_buffer_limit", config_buffer_limit))
    return response

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=[] if "*" in config_cors_origin and config_is_enable_cors_credentials == 1 else config_cors_origin, allow_origin_regex=".*" if "*" in config_cors_origin and config_is_enable_cors_credentials == 1 else None, allow_methods=config_cors_method, allow_headers=config_cors_headers, expose_headers=config_cors_expose_headers, allow_credentials=bool(config_is_enable_cors_credentials))
