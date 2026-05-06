#import
from .config import *
from .function import *
import aio_pika
import aiobotocore.session
import asyncpg
import asyncssh
import boto3
from google import genai
import httpx
import motor.motor_asyncio
import openai
import os
import redis.asyncio as redis
import sentry_sdk
import time
from argon2 import PasswordHasher
from aiokafka import AIOKafkaProducer
from azure.storage.blob.aio import BlobServiceClient
from celery import Celery
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from posthog import Posthog
from sentry_sdk.integrations.fastapi import FastApiIntegration

#lifespan
@asynccontextmanager
async def func_lifespan(app:FastAPI):
   #logging start
   start_journey = time.perf_counter()
   #structure
   for directory in ("tmp", "secret", "static"):os.makedirs(directory, exist_ok=True)
   #client init
   try:
       client_password_hasher = PasswordHasher()
       client_http = httpx.AsyncClient()
       client_postgres_pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=config_postgres_min_connection, max_size=config_postgres_max_connection) if config_postgres_url else None
       client_redis = redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url)) if config_redis_url else None
       client_redis_ratelimiter = redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url_ratelimiter)) if config_redis_url_ratelimiter else None
       client_redis_producer = redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url_pubsub)) if config_redis_url_pubsub else None
       client_mongodb = motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url) if config_mongodb_url else None
       client_s3 = aiobotocore.session.get_session().create_client("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key) if config_s3_region_name else None
       client_s3_resource = boto3.resource("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key) if config_s3_region_name else None
       client_sns = boto3.client("sns", region_name=config_sns_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key) if config_sns_region_name else None
       client_ses = boto3.client("ses", region_name=config_ses_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key) if config_ses_region_name else None
       client_openai = openai.OpenAI(api_key=config_openai_key) if config_openai_key else None
       if config_gemini_key:
          client_gemini = genai.Client(api_key=config_gemini_key)
       else:
          client_gemini = None
       client_posthog = Posthog(config_posthog_project_key, host=config_posthog_project_host) if config_posthog_project_key else None
       client_celery_producer = Celery("atom", broker=config_celery_broker_url, backend=config_celery_backend_url) if config_celery_broker_url else None
       if config_kafka_url:
          client_kafka_producer = AIOKafkaProducer(bootstrap_servers=config_kafka_url, security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaProducer(bootstrap_servers=config_kafka_url)
          await client_kafka_producer.start()
       else:
          client_kafka_producer = None
       if config_rabbitmq_url:
          client_rabbitmq = await aio_pika.connect_robust(config_rabbitmq_url)
          client_rabbitmq_producer = await client_rabbitmq.channel()
       else:
          client_rabbitmq = None
          client_rabbitmq_producer = None
       if config_sftp_host:
          if config_sftp_auth_method not in ("key", "password"): raise Exception(f"invalid sftp auth mode: {config_sftp_auth_method}")
          if config_sftp_auth_method == "key":
             if not config_sftp_key_path: raise Exception("ssh key path missing")
             client_sftp = await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, client_keys=[config_sftp_key_path], known_hosts=None)
          else:
             if not config_sftp_password: raise Exception("password missing")
             client_sftp = await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, password=config_sftp_password, known_hosts=None)
       else:
          client_sftp = None
       client_azure_blob = BlobServiceClient.from_connection_string(config_azure_connection_string) if config_azure_connection_string else BlobServiceClient(account_url=f"https://{config_azure_account_name}.blob.core.windows.net", credential=config_azure_account_key) if config_azure_account_name else None
       #postges schema init
       if client_postgres_pool and config_is_enable_postgres_init_startup == 1: await func_postgres_schema_init(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, config_postgres=config_postgres, config_postgres_root_user_password=config_postgres_root_user_password)
       #cache init
       cache_postgres_schema=await func_postgres_schema_read(client_postgres_pool=client_postgres_pool) if client_postgres_pool else {}
       cache_postgres_table_list=list(cache_postgres_schema.keys())
       cache_postgres_column_list=sorted(list(set(col for table in cache_postgres_schema.values() for col in table.keys())))
       cache_users_role = await func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=config_sql.get("sql_cache_users_role")) if client_postgres_pool else {}
       cache_users_is_active = await func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=config_sql.get("sql_cache_users_is_active")) if client_postgres_pool else {}
       cache_ratelimiter, cache_api_response, cache_postgres_buffer = {}, {}, {}
       #app state add
       for key, val in {**globals(),**locals()}.items():
          if key.startswith(("client_","cache_","config_","func_")): setattr(app.state, key, val)
       #openapi spec
       app.state.cache_openapi=func_openapi_spec_generate(app_routes=app.routes, config_api_roles_auth=config_api_roles_auth, app_state=app.state)
       #check
       await func_check(app_routes=app.routes, current_config_api=config_api, allowed_roles=config_api_roles, api_roles_auth=config_api_roles_auth, client_postgres_pool=client_postgres_pool)
   except Exception as e:
       print(f"❌ startup error: {e}")
       raise
   #ready
   #app shutdown
   yield
   if client_postgres_pool: await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="flush", table="", obj_list=[], is_serialize=0, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=None)
   if client_http: await client_http.aclose()
   if client_postgres_pool: await client_postgres_pool.close()
   if client_redis: await client_redis.aclose()
   if client_redis_ratelimiter: await client_redis_ratelimiter.aclose()
   if client_mongodb: client_mongodb.close()
   if client_posthog:
      client_posthog.shutdown()
      client_posthog.flush()
   if client_kafka_producer: await client_kafka_producer.stop()
   if client_rabbitmq_producer and not client_rabbitmq_producer.is_closed: await client_rabbitmq_producer.close()
   if client_rabbitmq and not client_rabbitmq.is_closed: await client_rabbitmq.close()
   if client_redis_producer: await client_redis_producer.aclose()
   if client_sftp:
      client_sftp.close()
      await client_sftp.wait_closed()
   if client_azure_blob: await client_azure_blob.close()

#app
app = FastAPI(debug=True, lifespan=func_lifespan, openapi_url=None, docs_url=None, redoc_url=None)

#router
func_app_router_add(app=app, router_dir=os.path.join(os.path.dirname(__file__), "router"), router_order={"index": 0, "auth": 1, "my": 2, "public": 3, "private": 4, "admin": 5})

#static
app.mount("/static", StaticFiles(directory="./static", check_dir=False), name="static")

#sentry
if config_sentry_dsn:
   sentry_sdk.init(dsn=config_sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=True)

#middleware
@app.middleware("http")
async def middleware(request, api_function):
    if request.method == "OPTIONS": return await api_function(request)
    start, error, request.state.user = time.perf_counter(), None, {}
    app_state = request.app.state
    try:
        request.state.user = await app_state.func_authenticate(headers=request.headers, url_path=request.url.path, config_token_secret_key=app_state.config_token_secret_key, config_api_roles_auth=app_state.config_api_roles_auth)
        await app_state.func_check_role(user_dict=request.state.user, url_path=request.url.path, config_api=app_state.config_api, client_postgres_pool=app_state.client_postgres_pool, client_redis=app_state.client_redis, cache_users_role=app_state.cache_users_role, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_check_is_active(user_dict=request.state.user, url_path=request.url.path, config_api=app_state.config_api, client_postgres_pool=app_state.client_postgres_pool, client_redis=app_state.client_redis, cache_users_is_active=app_state.cache_users_is_active, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_check_ratelimiter(client_redis_ratelimiter=app_state.client_redis_ratelimiter, config_api=app_state.config_api, url_path=request.url.path, identifier=request.state.user.get("id") if request.state.user else request.client.host, cache_ratelimiter=app_state.cache_ratelimiter)
        response = await app_state.func_api_response(request=request, api_function=api_function, config_api=app_state.config_api, client_redis=app_state.client_redis, user_id=request.state.user.get("id") if request.state.user else 0, cache_api_response=app_state.cache_api_response)
    except Exception as e:
        error, response = await app_state.func_api_response_error(exception=e, is_traceback=app_state.config_is_enable_traceback, sentry_dsn=app_state.config_sentry_dsn)
    await app_state.func_api_log_create(config_is_enable_log_api=app_state.config_is_enable_log_api, api_id=app_state.config_api.get(request.url.path, {}).get("id"), request=request, response=response, time_ms=int((time.perf_counter() - start) * 1000), user_id=request.state.user.get("id") if getattr(request.state, "user", None) else None, description=error, func_postgres_create=app_state.func_postgres_create, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer, config_table=app_state.config_table)
    return response

#cors add (must be at the end to be outermost)
app.add_middleware(CORSMiddleware, allow_origins=[] if "*" in config_cors_origin and config_is_enable_cors_credentials == 1 else config_cors_origin, allow_origin_regex=".*" if "*" in config_cors_origin and config_is_enable_cors_credentials == 1 else None, allow_methods=config_cors_method, allow_headers=config_cors_headers, expose_headers=config_cors_expose_headers, allow_credentials=bool(config_is_enable_cors_credentials))
