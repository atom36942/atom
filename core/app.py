#import
from function import *
from .config import *
from fastapi import FastAPI
from contextlib import asynccontextmanager
import httpx
import time

#lifespan
@asynccontextmanager
async def func_lifespan(app:FastAPI):
   #start
   func_structure_create(directories=["tmp","secret"], files=[".env"])
   #client init
   client_http=httpx.AsyncClient()
   client_postgres_pool=await func_client_read_postgres(config_postgres={"dsn":config_postgres_url,"min_size":config_postgres_min_connection,"max_size":config_postgres_max_connection}) if config_postgres_url else None
   client_redis=await func_client_read_redis(config_redis_url=config_redis_url) if config_redis_url else None
   client_redis_ratelimiter=await func_client_read_redis(config_redis_url=config_redis_url_ratelimiter) if config_redis_url_ratelimiter else None
   client_mongodb=func_client_read_mongodb(config_mongodb_uri=config_mongodb_uri) if config_mongodb_uri else None
   client_s3,client_s3_resource=(await func_client_read_s3(config_aws_access_key_id=config_aws_access_key_id, config_aws_secret_access_key=config_aws_secret_access_key, config_s3_region_name=config_s3_region_name)) if config_s3_region_name else (None, None)
   client_sns=func_client_read_sns(config_aws_access_key_id=config_aws_access_key_id, config_aws_secret_access_key=config_aws_secret_access_key, config_sns_region_name=config_sns_region_name) if config_sns_region_name else None
   client_ses=func_client_read_ses(config_aws_access_key_id=config_aws_access_key_id, config_aws_secret_access_key=config_aws_secret_access_key, config_ses_region_name=config_ses_region_name) if config_ses_region_name else None
   client_openai=func_client_read_openai(config_openai_key=config_openai_key) if config_openai_key else None
   client_posthog=func_client_read_posthog(config_posthog_project_host=config_posthog_project_host, config_posthog_project_key=config_posthog_project_key)
   client_celery_producer=func_client_read_celery_producer(config_celery_broker_url=config_celery_broker_url, config_celery_backend_url=config_celery_backend_url) if config_celery_broker_url else None
   client_kafka_producer=await func_client_read_kafka_producer(config_kafka_url=config_kafka_url, config_kafka_username=config_kafka_username, config_kafka_password=config_kafka_password) if config_kafka_url else None
   client_rabbitmq,client_rabbitmq_producer=await func_client_read_rabbitmq_producer(config_rabbitmq_url=config_rabbitmq_url) if config_rabbitmq_url else (None, None)
   client_redis_producer=await func_client_read_redis(config_redis_url=config_redis_url_pubsub) if config_redis_url_pubsub else None
   client_gsheet=func_client_read_gsheet(config_gsheet_service_account_json_path=config_gsheet_service_account_json_path, config_gsheet_scope=config_gsheet_scope) if config_gsheet_service_account_json_path else None
   client_sftp=await func_client_read_sftp(config_sftp_host=config_sftp_host, config_sftp_port=config_sftp_port, config_sftp_username=config_sftp_username, config_sftp_password=config_sftp_password, config_sftp_key_path=config_sftp_key_path, config_sftp_auth_method=config_sftp_auth_method) if config_sftp_host else None
   client_gemini=func_client_read_gemini(config_gemini_key=config_gemini_key) if config_gemini_key else None
   if client_postgres_pool and config_is_postgres_init_startup == 1:
      await func_postgres_init(client_postgres_pool=client_postgres_pool, config_postgres=config_postgres)
   #cache init
   cache_postgres_schema=await func_postgres_schema_read(client_postgres_pool=client_postgres_pool) if client_postgres_pool else {}
   cache_postgres_schema_tables=list(cache_postgres_schema.keys())
   cache_postgres_schema_columns=sorted(list(set(col for table in cache_postgres_schema.values() for col in table.keys())))
   cache_users_role=await func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=config_sql.get("cache_users_role")) if client_postgres_pool else {}
   cache_users_is_active=await func_postgres_map_column(client_postgres_pool=client_postgres_pool, config_sql=config_sql.get("cache_users_is_active")) if client_postgres_pool else {}
   cache_ratelimiter = {}
   cache_api_response = {}
   cache_postgres_buffer = {}
   #app state add
   func_app_state_add(app_obj=app, dict_context={**globals(),**locals()}, prefix_list=("client_","cache_","func_","config_"))
   app.state.cache_openapi=func_openapi_spec_generate(app_routes=app.routes, config_api_roles_auth=config_api_roles_auth, app_state=app.state)
   #check
   func_check(app_routes=app.routes, current_config_api=config_api, allowed_roles=config_api_roles, config_postgres=config_postgres, api_roles_auth=config_api_roles_auth)
   #app shutdown
   yield
   if client_postgres_pool:
      await func_postgres_create(client_postgres_pool=client_postgres_pool, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="flush", table="", obj_list=[], is_serialize=0, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer)
   if config_is_reset_tmp == 1:
      func_folder_reset(folder_path="tmp")
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
app=func_app_read(func_lifespan=func_lifespan)

#app add
func_app_add_cors(app_obj=app, config_cors_origin=config_cors_origin, config_cors_method=config_cors_method, config_cors_headers=config_cors_headers, config_is_cors_allow_credentials=config_is_cors_allow_credentials)
func_app_add_router(app_obj=app)
func_app_add_static(app_obj=app, folder_path="./static", route_path="/static")
if config_sentry_dsn:
   func_app_add_sentry(config_sentry_dsn=config_sentry_dsn)
if config_is_prometheus == 1:
   func_app_add_prometheus(app_obj=app)

#middleware
@app.middleware("http")
async def middleware(request, api_function):
    try:
        start, type, error, request.state.user = time.perf_counter(), None, None, {}
        st = request.app.state
        request.state.user = await st.func_authenticate(headers=request.headers, url_path=request.url.path, config_token_secret_key=st.config_token_secret_key, config_api_roles_auth=st.config_api_roles_auth)
        await st.func_check_admin(user_dict=request.state.user, url_path=request.url.path, config_api=st.config_api, client_postgres_pool=st.client_postgres_pool, client_redis=st.client_redis, cache_users_role=st.cache_users_role, config_redis_cache_ttl_sec=st.config_redis_cache_ttl_sec)
        await st.func_check_is_active(user_dict=request.state.user, url_path=request.url.path, config_api=st.config_api, client_postgres_pool=st.client_postgres_pool, client_redis=st.client_redis, cache_users_is_active=st.cache_users_is_active, config_redis_cache_ttl_sec=st.config_redis_cache_ttl_sec)
        await st.func_check_ratelimiter(client_redis_ratelimiter=st.client_redis_ratelimiter, config_api=st.config_api, url_path=request.url.path, identifier=request.state.user.get("id") if request.state.user else request.client.host, cache_ratelimiter=st.cache_ratelimiter)
        response, type = await st.func_api_response(request=request, api_function=api_function, config_api=st.config_api, client_redis=st.client_redis, user_id=request.state.user.get("id") if request.state.user else 0, func_background=st.func_api_response_background, func_cache=st.func_check_cache, cache_api_response=st.cache_api_response)
    except Exception as e:
        error, response = await request.app.state.func_api_response_error(exception=e, is_traceback=request.app.state.config_is_traceback, sentry_dsn=request.app.state.config_sentry_dsn)
    await request.app.state.func_api_log_create(config_is_log_api=request.app.state.config_is_log_api, api_id=request.app.state.config_api.get(request.url.path, {}).get("id"), request=request, response=response, time_ms=int((time.perf_counter() - start) * 1000), user_id=request.state.user.get("id") if getattr(request.state, "user", None) else None, func_postgres_create=request.app.state.func_postgres_create, client_postgres_pool=request.app.state.client_postgres_pool, func_postgres_serialize=request.app.state.func_postgres_serialize, cache_postgres_schema=request.app.state.cache_postgres_schema, cache_postgres_buffer=request.app.state.cache_postgres_buffer, config_table=request.app.state.config_table)
    return response
