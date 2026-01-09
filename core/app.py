#import
from core.function import *
from core.config import *
from fastapi import FastAPI,responses
from contextlib import asynccontextmanager
import traceback,os,time
from pathlib import Path

#lifespan
@asynccontextmanager
async def func_lifespan(app:FastAPI):
   try:
      #start
      os.makedirs("export",exist_ok=True)
      #client init
      client_postgres_pool=await func_postgres_client_read(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
      client_redis=await func_redis_client_read(config_redis_url) if config_redis_url else None
      client_redis_ratelimiter=await func_redis_client_read(config_redis_url_ratelimiter) if config_redis_url_ratelimiter else None
      client_mongodb=await func_mongodb_client_read(config_mongodb_url) if config_mongodb_url else None
      client_s3,client_s3_resource=(await func_s3_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name)) if config_s3_region_name else (None, None)
      client_sns=await func_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name) if config_sns_region_name else None
      client_ses=await func_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name) if config_ses_region_name else None
      client_openai=func_openai_client_read(config_openai_key) if config_openai_key else None
      client_posthog=await func_posthog_client_read(config_posthog_project_host,config_posthog_project_key)
      client_celery_producer=await func_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url) if config_celery_broker_url else None
      client_kafka_producer=await func_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password) if config_kafka_url else None
      client_rabbitmq,client_rabbitmq_producer=await func_rabbitmq_client_read_producer(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
      client_redis_producer=await func_redis_client_read(config_redis_url_pubsub) if config_redis_url_pubsub else None
      client_gsheet=func_gsheet_client_read(config_gsheet_service_account_json_path, config_gsheet_scope_list) if config_gsheet_service_account_json_path else None
      client_sftp=await func_sftp_client_read(config_sftp_host,config_sftp_port,config_sftp_username,config_sftp_password,config_sftp_key_path,config_sftp_auth_method) if config_sftp_host else None
      #cache init
      cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else ({},{})
      cache_users_api_access=await func_postgres_map_column(client_postgres_pool,config_sql.get("cache_users_api_access")) if client_postgres_pool and cache_postgres_schema.get("users",{}).get("api_access") else {}
      cache_users_is_active=await func_postgres_map_column(client_postgres_pool,config_sql.get("cache_users_is_active")) if client_postgres_pool and cache_postgres_schema.get("users",{}).get("is_active") else {}
      cache_config=await func_postgres_map_column(client_postgres_pool,config_sql.get("cache_config")) if client_postgres_pool and cache_postgres_schema.get("config",{}) else {}
      #app state set
      func_app_state_add(app,{**globals(),**locals()},("func_","config_","client_","cache_"))
      #app shutdown
      yield
      await func_postgres_obj_create(client_postgres_pool,func_postgres_obj_serialize,cache_postgres_column_datatype,"flush")
      if config_is_reset_export_folder:func_folder_reset("export")
      if client_postgres_pool:await client_postgres_pool.close()
      if client_redis:await client_redis.aclose()
      if client_redis_ratelimiter:await client_redis_ratelimiter.aclose()
      if client_mongodb:client_mongodb.close()
      if client_posthog:client_posthog.shutdown()
      if client_posthog:client_posthog.flush()
      if client_kafka_producer:await client_kafka_producer.stop()
      if client_rabbitmq_producer and not client_rabbitmq_producer.is_closed:await client_rabbitmq_producer.close()
      if client_rabbitmq and not client_rabbitmq.is_closed:await client_rabbitmq.close()
      if client_redis_producer:await client_redis_producer.aclose()
      if client_sftp:
         client_sftp.close()
         await client_sftp.wait_closed()
   except Exception as e:
      print(str(e))
      print(traceback.format_exc())
      
#app
app=func_app_create(func_lifespan,config_is_debug_fastapi)
func_app_add_cors(app,config_cors_origin_list,config_cors_method_list,config_cors_headers_list,config_cors_allow_credentials)
func_app_add_router(app,config_folder_router_list)
if config_sentry_dsn:func_app_add_sentry(config_sentry_dsn)
if config_is_prometheus:func_app_add_prometheus(app)

#middleware
@app.middleware("http")
async def middleware(request,api_function):
   try:
      start,type,error,request.state.user=time.perf_counter(),None,None,{}
      request.state.user=await func_handler_token(request)
      await func_handler_admin(request)
      await func_handler_is_active(request)
      await func_handler_ratelimiter(request)
      response,type=await func_handler_api_response(request,api_function)
   except Exception as e:error,response=await func_handler_api_error(request,e)
   await func_handler_log_api(start,request,response,type,error)
   return response

#root
@app.get("/")
async def func_api_index():
   html_path=await func_path_read(config_folder_html_list,f"{config_project_name}.html")
   if not html_path:return {"status":1,"message":"welcome to atom"}
   return responses.HTMLResponse(content=await func_read_html(html_path))

