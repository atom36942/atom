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
   func_structure_create(["tmp","secret"], [".env"])
   #client init
   client_http=httpx.AsyncClient()
   client_postgres_pool=await func_postgres_client_read({"dsn":config_postgres_url,"min_size":config_postgres_min_connection,"max_size":config_postgres_max_connection}) if config_postgres_url else None
   client_redis=await func_redis_client_read(config_redis_url) if config_redis_url else None
   client_redis_ratelimiter=await func_redis_client_read(config_redis_url_ratelimiter) if config_redis_url_ratelimiter else None
   client_mongodb=func_mongodb_client_read(config_mongodb_uri) if config_mongodb_uri else None
   client_s3,client_s3_resource=(await func_s3_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name)) if config_s3_region_name else (None, None)
   client_sns=func_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name) if config_sns_region_name else None
   client_ses=func_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name) if config_ses_region_name else None
   client_openai=func_openai_client_read(config_openai_key) if config_openai_key else None
   client_posthog=func_posthog_client_read(config_posthog_project_host,config_posthog_project_key)
   client_celery_producer=func_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url) if config_celery_broker_url else None
   client_kafka_producer=await func_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password) if config_kafka_url else None
   client_rabbitmq,client_rabbitmq_producer=await func_rabbitmq_client_read_producer(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
   client_redis_producer=await func_redis_client_read(config_redis_url_pubsub) if config_redis_url_pubsub else None
   client_gsheet=func_gsheet_client_read(config_gsheet_service_account_json_path, config_gsheet_scope) if config_gsheet_service_account_json_path else None
   client_sftp=await func_sftp_client_read(config_sftp_host,config_sftp_port,config_sftp_username,config_sftp_password,config_sftp_key_path,config_sftp_auth_method) if config_sftp_host else None
   client_gemini=func_gemini_client_read(config_gemini_key) if config_gemini_key else None
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
import time,json
@app.middleware("http")
async def middleware(request,api_function):
   try:
      start,type,error,request.state.user=time.perf_counter(),None,None,{}
      st=request.app.state
      request.state.user=await st.func_authenticate(request.headers,request.url.path,st.config_token_secret_key,st.config_api_roles_auth)
      await st.func_check_admin(request.state.user,request.url.path,st.config_api,st.client_postgres_pool,st.client_redis,st.cache_users_role,st.config_redis_cache_ttl_sec)
      await st.func_check_is_active(request.state.user,request.url.path,st.config_api,st.client_postgres_pool,st.client_redis,st.cache_users_is_active,st.config_redis_cache_ttl_sec)
      await st.func_check_ratelimiter(st.client_redis_ratelimiter,st.config_api,request.url.path,request.state.user.get("id") if request.state.user else request.client.host)
      response,type=await st.func_api_response(request,api_function,st.config_api,st.client_redis,request.state.user.get("id") if request.state.user else 0,st.func_api_response_background,st.func_check_cache)
   except Exception as e:
      error,response=await request.app.state.func_api_response_error(e,request.app.state.config_is_traceback,request.app.state.config_sentry_dsn)
   await request.app.state.func_api_log_create(request.app.state.config_is_log_api, request.app.state.config_api.get(request.url.path, {}).get("id"), request, response, int((time.perf_counter() - start) * 1000), request.state.user.get("id") if getattr(request.state, "user", None) else None, request.app.state.func_postgres_create, request.app.state.client_postgres_pool, request.app.state.func_postgres_obj_serialize, request.app.state.config_table)
   return response

#main
import os
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
   