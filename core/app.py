#config
from core.config import *

#function
from core.function import *

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import traceback
@asynccontextmanager
async def function_lifespan(app:FastAPI):
   try:
      #checks
      function_create_folder("export")
      if config_is_reset_export_folder:function_reset_folder("export")
      #client init
      client_postgres_pool=await function_postgres_client_read(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection,config_postgres_schema_name) if config_postgres_url else None
      client_redis=await function_redis_client_read(config_redis_url) if config_redis_url else None
      client_redis_ratelimiter=await function_redis_client_read(config_redis_url_ratelimiter) if config_redis_url_ratelimiter else None
      client_mongodb=await function_mongodb_client_read(config_mongodb_url) if config_mongodb_url else None
      client_s3,client_s3_resource=(await function_s3_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name)) if config_s3_region_name else (None, None)
      client_sns=await function_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name) if config_sns_region_name else None
      client_ses=await function_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name) if config_ses_region_name else None
      client_openai=function_openai_client_read(config_openai_key) if config_openai_key else None
      client_posthog=await function_posthog_client_read(config_posthog_project_host,config_posthog_project_key)
      client_celery_producer=await function_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url) if config_celery_broker_url else None
      client_kafka_producer=await function_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password) if config_kafka_url else None
      client_rabbitmq,client_rabbitmq_producer=await function_rabbitmq_client_read_producer(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
      client_redis_producer=await function_redis_client_read(config_redis_url_pubsub) if config_redis_url_pubsub else None
      client_gsheet=function_gsheet_client_read(config_gsheet_service_account_json_path, config_gsheet_scope_list) if config_gsheet_service_account_json_path else None
      client_sftp=await function_sftp_client_read(config_sftp_host,config_sftp_port,config_sftp_username,config_sftp_password,config_sftp_key_path,config_sftp_auth_method) if config_sftp_host else None
      #cache init
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      cache_users_api_access=await function_postgres_map_column(client_postgres_pool,config_sql.get("cache_users_api_access")) if client_postgres_pool and cache_postgres_schema.get("users",{}).get("api_access") else {}
      cache_users_is_active=await function_postgres_map_column(client_postgres_pool,config_sql.get("cache_users_is_active")) if client_postgres_pool and cache_postgres_schema.get("users",{}).get("is_active") else {}
      cache_config=await function_postgres_map_column(client_postgres_pool,config_sql.get("cache_config")) if client_postgres_pool and cache_postgres_schema.get("config",{}) else {}
      #app state set
      function_add_state(app,{**globals(),**locals()},("client_","cache_"))
      #app shutdown
      yield
      await function_postgres_object_create(client_postgres_pool,function_postgres_object_serialize,cache_postgres_column_datatype,"flush")
      if config_is_reset_export_folder:function_reset_folder("export")
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
app=function_fastapi_app_read(function_lifespan,config_is_debug_fastapi)
function_add_cors(app,config_cors_origin_list,config_cors_method_list,config_cors_headers_list,config_cors_allow_credentials)
if config_sentry_dsn:function_add_sentry(config_sentry_dsn)
if config_is_prometheus:function_add_prometheus(app)

#router
from pathlib import Path
router_dir_path = Path(__file__).parent.parent / "router"
function_add_router(app, router_dir_path)

#middleware
from fastapi import Request,responses
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
   try:
      #start
      start=time.time()
      api=request.url.path
      request.state.user={}
      response_type=None
      error=None
      #check
      request.state.user=await function_token_check(request,config_api,config_key_root,config_key_jwt,function_token_decode)
      await function_check_admin(config_mode_check_api_access,config_api,request)
      await function_check_is_active(config_mode_check_is_active,config_api,request)
      await function_check_ratelimiter(config_api,request)
      #response
      response,response_type=await function_api_response(request,api_function,config_api,function_api_response_background,function_api_response_cache)
   #error
   except Exception as e:
      error=str(e)
      if config_is_traceback:print(traceback.format_exc())
      response=responses.JSONResponse(status_code=400,content={"status":0,"message":error})
      if config_sentry_dsn:sentry_sdk.capture_exception(e)
   #log api
   if config_is_log_api:
      obj_log={"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"api_id":config_api.get(api,{}).get("id"),"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"response_type":response_type,"description":error}
      asyncio.create_task(function_postgres_object_create(request.app.state.client_postgres_pool,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,"buffer","log_api",[obj_log],0,config_table.get("log_api",{}).get("buffer",10)))
   #posthog
   if False:request.app.state.client_posthog.capture(distinct_id=request.state.user.get("id"),event="api",properties=obj_log)
   #final
   return response

#root
@app.get("/")
async def function_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"}