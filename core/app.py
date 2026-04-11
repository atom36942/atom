#import
from .function import *
from function.client import *
from function.middleware import *
from .config import *

#libraries (for injection)
import asyncpg
import redis.asyncio as redis_lib
import motor.motor_asyncio
import aiobotocore.session
import boto3
import openai
from posthog import Posthog
from celery import Celery
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import aio_pika
import gspread
from google.oauth2.service_account import Credentials
import asyncssh
import google.generativeai as genai

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import httpx
@asynccontextmanager
async def func_lifespan(app:FastAPI):
   #start
   func_structure_create(["tmp","secret"], [".env"])
   #client init
   client_http=httpx.AsyncClient()
   client_postgres_pool=await func_client_read_postgres({"dsn":config_postgres_url,"min_size":config_postgres_min_connection,"max_size":config_postgres_max_connection}, asyncpg) if config_postgres_url else None
   client_redis=await func_client_read_redis(config_redis_url, redis_lib) if config_redis_url else None
   client_redis_ratelimiter=await func_client_read_redis(config_redis_url_ratelimiter, redis_lib) if config_redis_url_ratelimiter else None
   client_mongodb=func_client_read_mongodb(config_mongodb_uri, motor_asyncio) if config_mongodb_uri else None
   client_s3,client_s3_resource=(await func_client_read_s3(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name, aiobotocore, boto3)) if config_s3_region_name else (None, None)
   client_sns=func_client_read_sns(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name, boto3) if config_sns_region_name else None
   client_ses=func_client_read_ses(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name, boto3) if config_ses_region_name else None
   client_openai=func_client_read_openai(config_openai_key, openai.OpenAI) if config_openai_key else None
   client_posthog=func_client_read_posthog(config_posthog_project_host,config_posthog_project_key, Posthog)
   client_celery_producer=func_client_read_celery_producer(config_celery_broker_url,config_celery_backend_url, Celery) if config_celery_broker_url else None
   client_kafka_producer=await func_client_read_kafka_producer(config_kafka_url, AIOKafkaProducer, config_kafka_username, config_kafka_password) if config_kafka_url else None
   client_rabbitmq,client_rabbitmq_producer=await func_client_read_rabbitmq_producer(config_rabbitmq_url, aio_pika) if config_rabbitmq_url else (None, None)
   client_redis_producer=await func_client_read_redis(config_redis_url_pubsub, redis_lib) if config_redis_url_pubsub else None
   client_gsheet=func_client_read_gsheet(config_gsheet_service_account_json_path, config_gsheet_scope, gspread, Credentials) if config_gsheet_service_account_json_path else None
   client_sftp=await func_client_read_sftp(config_sftp_host,config_sftp_port,config_sftp_username,config_sftp_password,config_sftp_key_path,config_sftp_auth_method, asyncssh) if config_sftp_host else None
   client_gemini=func_client_read_gemini(config_gemini_key, genai) if config_gemini_key else None
   if client_postgres_pool and config_is_postgres_init_startup == 1:
      await func_postgres_init(client_postgres_pool, config_postgres)
   #cache init
   cache_postgres_schema=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else {}
   cache_postgres_schema_tables=list(cache_postgres_schema.keys())
   cache_postgres_schema_columns=sorted(list(set(col for table in cache_postgres_schema.values() for col in table.keys())))
   cache_users_role=await func_sql_map_column(client_postgres_pool,config_sql.get("cache_users_role")) if client_postgres_pool else {}
   cache_users_is_active=await func_sql_map_column(client_postgres_pool,config_sql.get("cache_users_is_active")) if client_postgres_pool else {}
   #app state add
   func_app_state_add(app,{**globals(),**locals()},("func_","config_","client_","cache_"))
   app.state.cache_openapi=func_openapi_spec_generate(app.routes, config_api_roles_auth, app.state)
   #check
   func_check(app.routes, config_api, config_api_roles, config_postgres, config_api_roles_auth)
   #app shutdown
   yield
   await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "flush", None, None)
   if config_is_reset_tmp == 1:
      func_folder_reset("tmp")
   await client_http.aclose()
   if client_postgres_pool:
      await client_postgres_pool.close()
   if client_redis:
      await client_redis.aclose()
   if client_redis_ratelimiter:
      await client_redis_ratelimiter.aclose()
   if client_mongodb:
      client_mongodb.close()
   if client_posthog:
      client_posthog.shutdown()
   if client_posthog:
      client_posthog.flush()
   if client_kafka_producer:
      await client_kafka_producer.stop()
   if client_rabbitmq_producer and not client_rabbitmq_producer.is_closed:
      await client_rabbitmq_producer.close()
   if client_rabbitmq and not client_rabbitmq.is_closed:
      await client_rabbitmq.close()
   if client_redis_producer:
      await client_redis_producer.aclose()
   if client_sftp:
      client_sftp.close()
      await client_sftp.wait_closed()
      
#app
app=func_fastapi_app_read(func_lifespan,config_is_debug_fastapi)

#app add
func_app_add_cors(app,config_cors_origin,config_cors_method,config_cors_headers,config_is_cors_allow_credentials)
func_add_router(app)
func_app_add_static(app,"./static","/static")
if config_sentry_dsn:
   func_app_add_sentry(config_sentry_dsn)
if config_is_prometheus == 1:
   func_app_add_prometheus(app)

#middleware
func_app_add_middleware(app)
