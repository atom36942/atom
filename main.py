#import
from function import *
from config import *

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import httpx
@asynccontextmanager
async def func_lifespan(app:FastAPI):
   #start
   func_structure_create(["tmp","secret"], [".env","z.py"])
   #client init
   client_http=httpx.AsyncClient()
   client_postgres_pool=await func_postgres_client_read({"dsn":config_postgres_url,"min_size":config_postgres_min_connection,"max_size":config_postgres_max_connection}) if config_postgres_url else None
   client_redis=await func_redis_client_read(config_redis_url) if config_redis_url else None
   client_redis_ratelimiter=await func_redis_client_read(config_redis_url_ratelimiter) if config_redis_url_ratelimiter else None
   client_mongodb=await func_mongodb_client_read(config_mongodb_url) if config_mongodb_url else None
   client_s3,client_s3_resource=(await func_s3_client_read({"aws_access_key_id":config_aws_access_key_id,"aws_secret_access_key":config_aws_secret_access_key,"region_name":config_s3_region_name})) if config_s3_region_name else (None, None)
   client_sns=await func_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name) if config_sns_region_name else None
   client_ses=await func_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name) if config_ses_region_name else None
   client_openai=func_openai_client_read(config_openai_key) if config_openai_key else None
   client_posthog=await func_posthog_client_read(config_posthog_project_host,config_posthog_project_key)
   client_celery_producer=await func_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url) if config_celery_broker_url else None
   client_kafka_producer=await func_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password) if config_kafka_url else None
   client_rabbitmq,client_rabbitmq_producer=await func_rabbitmq_client_read_producer(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
   client_redis_producer=await func_redis_client_read(config_redis_url_pubsub) if config_redis_url_pubsub else None
   client_gsheet=func_gsheet_client_read(config_gsheet_service_account_json_path, config_gsheet_scope) if config_gsheet_service_account_json_path else None
   client_sftp=await func_sftp_client_read(config_sftp_host,config_sftp_port,config_sftp_username,config_sftp_password,config_sftp_key_path,config_sftp_auth_method) if config_sftp_host else None
   client_gemini=await func_gemini_client_read(config_gemini_key) if config_gemini_key else None
   #cache init
   cache_postgres_schema=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else {}
   cache_users_role=await func_sql_map_column(client_postgres_pool,config_sql.get("cache_users_role")) if client_postgres_pool and cache_postgres_schema.get("users",{}).get("role") else {}
   cache_users_is_active=await func_sql_map_column(client_postgres_pool,config_sql.get("cache_users_is_active")) if client_postgres_pool and cache_postgres_schema.get("users",{}).get("is_active") else {}
   #app state set
   func_app_state_add(app,{**globals(),**locals()},("func_","config_","client_","cache_"))
   #app shutdown
   yield
   await func_postgres_obj_create(client_postgres_pool, func_postgres_obj_serialize, "flush")
   if config_is_reset_export_folder:func_folder_reset("tmp")
   await client_http.aclose()
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
      
#app
app=func_fastapi_app_read(func_lifespan,config_is_debug_fastapi)

#app add
func_app_add_cors(app,config_cors_origin,config_cors_method,config_cors_headers,config_cors_allow_credentials)
func_add_router(app)
func_app_add_static(app,"./static","/static")
if config_sentry_dsn:func_app_add_sentry(config_sentry_dsn)
if config_is_prometheus:func_app_add_prometheus(app)

#middleware
import time,json
@app.middleware("http")
async def middleware(request,api_function):
   try:
      start,type,error,request.state.user=time.perf_counter(),None,None,{}
      st=request.app.state
      request.state.user=await st.func_check_token(request.headers,request.url.path,st.config_key_root,st.config_token_secret_key,st.config_api,st.func_token_decode)
      await st.func_check_admin(st.config_mode_check_admin,request.state.user,request.url.path,st.config_api,st.client_postgres_pool,st.cache_users_role)
      await st.func_check_is_active(st.config_mode_check_active,request.state.user,request.url.path,st.config_api,st.client_postgres_pool,st.cache_users_is_active)
      await st.func_check_ratelimiter(st.client_redis_ratelimiter,st.config_api,request.url.path,request.state.user.get("id") if request.state.user else request.client.host)
      response,type=await st.func_api_response(request,api_function,st.config_api,st.client_redis,request.state.user.get("id") if request.state.user else 0,st.func_api_response_background,st.func_check_cache)
   except Exception as e:error,response=await request.app.state.func_api_response_error(e,request.app.state.config_is_traceback,request.app.state.config_sentry_dsn)
   await request.app.state.func_api_log_create(start,request.client.host,request.state.user.get("id") if getattr(request.state,"user",None) else None,request.url.path,request.method,json.dumps(dict(request.query_params)),response.status_code if response else 0,type,error,request.app.state.config_is_log_api,request.app.state.config_api.get(request.url.path,{}).get("id"),request.app.state.func_postgres_obj_create,request.app.state.client_postgres_pool,request.app.state.func_postgres_obj_serialize,request.app.state.config_table.get("log_api",{}).get("buffer") if request.app.state.config_table else 10)
   return response

#main
from function import func_server_start
import asyncio
if __name__=="__main__":
   try:asyncio.run(func_server_start(app))
   except KeyboardInterrupt:print("exit")
   