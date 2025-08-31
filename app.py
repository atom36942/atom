#function
from function import *

#config
from config import *

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import traceback
@asynccontextmanager
async def lifespan(app:FastAPI):
   try:
      #client init
      client_postgres=await function_client_read_postgres(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
      client_postgres_asyncpg=await function_client_read_postgres_asyncpg(config_postgres_url) if config_postgres_url else None
      client_postgres_asyncpg_pool=await function_client_read_postgres_asyncpg_pool(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
      client_postgres_read=await function_client_read_postgres(config_postgres_url_read,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url_read else None
      client_redis=await function_client_read_redis(config_redis_url) if config_redis_url else None
      client_redis_ratelimiter=await function_client_read_redis(config_redis_url_ratelimiter) if config_redis_url_ratelimiter else None
      client_mongodb=await function_client_read_mongodb(config_mongodb_url) if config_mongodb_url else None
      client_s3,client_s3_resource=(await function_client_read_s3(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name)) if config_s3_region_name else (None, None)
      client_sns=await function_client_read_sns(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name) if config_sns_region_name else None
      client_ses=await function_client_read_ses(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name) if config_ses_region_name else None
      client_openai=function_client_read_openai(config_openai_key) if config_openai_key else None
      client_posthog=await function_client_read_posthog(config_posthog_project_host,config_posthog_project_key)
      client_celery_producer=await function_client_read_celery_producer(config_celery_broker_url,config_celery_backend_url) if config_celery_broker_url else None
      client_kafka_producer=await function_client_read_kafka_producer(config_kafka_url,config_kafka_username,config_kafka_password) if config_kafka_url else None
      client_rabbitmq,client_rabbitmq_producer=await function_client_read_rabbitmq_producer(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
      client_redis_producer=await function_client_read_redis(config_redis_pubsub_url) if config_redis_pubsub_url else None
      #cache init
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres) if client_postgres else (None, None)
      cache_users_api_access=await function_column_mapping_read(client_postgres_asyncpg,"users","id","api_access",config_limit_cache_users_api_access,0,"split_int") if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("api_access") else {}
      cache_users_is_active=await function_column_mapping_read(client_postgres_asyncpg,"users","id","is_active",config_limit_cache_users_api_access,1,None) if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("is_active") else {}
      #app state set
      function_add_app_state({**globals(),**locals()},app,("client_","cache_"))
      #app shutdown
      yield
      await function_log_create_postgres("flush",function_object_create_postgres,client_postgres,None,None)
      await function_object_create_postgres_batch("flush",function_object_create_postgres,client_postgres,None,None,None,1,function_object_serialize,cache_postgres_column_datatype)
      if client_postgres:await client_postgres.disconnect()
      if client_postgres_asyncpg:await client_postgres_asyncpg.close()
      if client_postgres_asyncpg_pool:await client_postgres_asyncpg_pool.close()
      if client_postgres_read:await client_postgres_read.close()
      if client_redis:await client_redis.aclose()
      if client_redis_ratelimiter:await client_redis_ratelimiter.aclose()
      if client_redis_producer:await client_redis_producer.aclose()
      if client_mongodb:client_mongodb.close()
      if client_kafka_producer:await client_kafka_producer.stop()
      if client_rabbitmq_producer and not client_rabbitmq_producer.is_closed:await client_rabbitmq_producer.close()
      if client_rabbitmq and not client_rabbitmq.is_closed:await client_rabbitmq.close()
      if client_posthog:client_posthog.flush()
      if client_posthog:client_posthog.shutdown()
      function_delete_files(".",[".csv"],["export_"])
   except Exception as e:
      print(str(e))
      print(traceback.format_exc())

#app
app=function_fastapi_app_read(True,lifespan)

#cors
function_add_cors(app,config_cors_origin_list,config_cors_method_list,config_cors_headers_list,config_cors_allow_credentials)

#router
function_add_router(app,"router")

#sentry
if config_sentry_dsn:function_add_sentry(config_sentry_dsn)

#prometheus
if config_is_prometheus:function_add_prometheus(app)

#middleware
from fastapi import Request,responses
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
   try:
      #start
      start=time.time()
      response_type=None
      response=None
      error=None
      api=request.url.path
      request.state.user={}
      #auth check
      request.state.user=await function_token_check(request,config_key_root,config_key_jwt,config_api,function_token_decode)
      #admin check
      if "admin/" in api:await function_check_api_access(config_mode_check_api_access,request,request.app.state.cache_users_api_access,request.app.state.client_postgres,config_api)
      #active check
      if config_api.get(api,{}).get("is_active_check")==1 and request.state.user:await function_check_is_active(config_mode_check_is_active,request,request.app.state.cache_users_is_active,request.app.state.client_postgres)
      #ratelimiter check
      if config_api.get(api,{}).get("ratelimiter_times_sec"):await function_check_ratelimiter(request,request.app.state.client_redis_ratelimiter,config_api)
      #background response
      if request.query_params.get("is_background")=="1":
         response=await function_api_response_background(request,api_function)
         response_type=1
      #cache response
      elif config_api.get(api,{}).get("cache_sec"):
         response=await function_cache_api_response("get",request,None,request.app.state.client_redis,config_api)
         response_type=2
      #default response
      if not response:
         response=await api_function(request)
         response_type=3
         if config_api.get(api,{}).get("cache_sec"):
            response=await function_cache_api_response("set",request,response,request.app.state.client_redis,config_api)
            response_type=4
   #error
   except Exception as e:
      error=str(e)
      if config_is_traceback:print(traceback.format_exc())
      response=responses.JSONResponse(status_code=400,content={"status":0,"message":error})
      if config_sentry_dsn:sentry_sdk.capture_exception(e)
      response_type=5
   #log api
   if config_is_log_api and getattr(request.app.state, "cache_postgres_schema", None) and request.app.state.cache_postgres_schema.get("log_api"):
      obj_log={"response_type":response_type,"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"api_id":config_api.get(api,{}).get("id"),"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"description":error}
      asyncio.create_task(function_log_create_postgres("append",function_object_create_postgres,request.app.state.client_postgres,config_batch_log_api,obj_log))
   #final
   return response

#root
@app.get("/")
async def function_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"}