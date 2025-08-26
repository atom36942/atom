#function
from function import *

#config
config=function_config_read()
config_postgres_url=config.get("config_postgres_url")
config_postgres_url_read=config.get("config_postgres_url_read")
config_postgres_min_connection=int(config.get("config_postgres_min_connection",5))
config_postgres_max_connection=int(config.get("config_postgres_max_connection",20))
config_redis_url=config.get("config_redis_url")
config_redis_url_ratelimiter=config.get("config_redis_url_ratelimiter",config_redis_url)
config_mongodb_url=config.get("config_mongodb_url")
config_celery_broker_url=config.get("config_celery_broker_url")
config_rabbitmq_url=config.get("config_rabbitmq_url")
config_kafka_url=config.get("config_kafka_url")
config_kafka_username=config.get("config_kafka_username")
config_kafka_password=config.get("config_kafka_password")
config_redis_pubsub_url=config.get("config_redis_pubsub_url")
config_aws_access_key_id=config.get("config_aws_access_key_id")
config_aws_secret_access_key=config.get("config_aws_secret_access_key")
config_s3_region_name=config.get("config_s3_region_name")
config_sns_region_name=config.get("config_sns_region_name")
config_ses_region_name=config.get("config_ses_region_name")
config_fast2sms_url=config.get("config_fast2sms_url")
config_fast2sms_key=config.get("config_fast2sms_key")
config_resend_url=config.get("config_resend_url")
config_resend_key=config.get("config_resend_key")
config_posthog_project_host=config.get("config_posthog_project_host")
config_posthog_project_key=config.get("config_posthog_project_key")
config_key_root=config.get("config_key_root")
config_key_jwt=config.get("config_key_jwt")
config_sentry_dsn=config.get("config_sentry_dsn")
config_google_login_client_id=config.get("config_google_login_client_id")
config_openai_key=config.get("config_openai_key")
config_mode_check_api_access=config.get("config_mode_check_api_access","token")
config_mode_check_is_active=config.get("config_mode_check_is_active","token")
config_token_expire_sec=int(config.get("config_token_expire_sec",365*24*60*60))
config_is_signup=int(config.get("config_is_signup",1))
config_is_log_api=int(config.get("config_is_log_api",1))
config_is_traceback=int(config.get("config_is_traceback",0))
config_is_prometheus=int(config.get("config_is_prometheus",0))
config_is_otp_verify_profile_update=int(config.get("config_is_otp_verify_profile_update",1))
config_batch_log_api=int(config.get("config_batch_log_api",10))
config_batch_object_create=int(config.get("config_batch_object_create",3))
config_limit_cache_users_api_access=int(config.get("config_limit_cache_users_api_access",0))
config_limit_cache_users_is_active=int(config.get("config_limit_cache_users_is_active",0))
config_token_user_key_list=config.get("config_token_user_key_list","id,type,is_active,api_access").split(",")
config_column_update_disabled_list=config.get("config_column_update_disabled_list","is_active,is_verified,api_access").split(",")
config_public_table_create_list=config.get("config_public_table_create_list","test").split(",")
config_public_table_read_list=config.get("config_public_table_read_list","test").split(",")
config_cors_origin_list=config.get("config_cors_origin_list","*").split(",")
config_cors_method_list=config.get("config_cors_method_list","*").split(",")
config_cors_headers_list=config.get("config_cors_headers_list","*").split(",")
config_cors_allow_credentials=config.get("config_cors_allow_credentials",False)
config_api=config.get("config_api",{})
config_postgres_schema=config.get("config_postgres_schema",{})
config_postgres_clean={
"log_api":365,
"otp":365,
}

config_user_count_key={
"log_api_count":"select count(*) from log_api where created_by_id=:user_id",
"test_count":"select count(*) from test where created_by_id=:user_id"
}

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import traceback,asyncio
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
      client_celery_producer=await function_client_read_celery_producer(config_celery_broker_url,config_celery_broker_url) if config_celery_broker_url else None
      client_kafka_producer=await function_client_read_kafka_producer(config_kafka_url,config_kafka_username,config_kafka_password) if config_kafka_url else None
      client_rabbitmq,client_rabbitmq_producer=await function_client_read_rabbitmq_producer(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
      client_redis_producer=await function_client_read_redis(config_redis_pubsub_url) if config_redis_pubsub_url else None
      #cache init
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres) if client_postgres else (None, None)
      cache_users_api_access=await function_column_mapping_read(client_postgres_asyncpg,"users","id","api_access",config_limit_cache_users_api_access,0,"split_int") if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("api_access") else {}
      cache_users_is_active=await function_column_mapping_read(client_postgres_asyncpg,"users","id","is_active",config_limit_cache_users_api_access,1,None) if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("is_active") else {}
      #app state set
      function_add_app_state({**globals(),**locals()},app,("config_","client_","cache_"))
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
function_add_cors(app,config_cors_origin_list,config_cors_method_list,config_cors_headers_list,config_cors_allow_credentials)
function_add_router(app,"router")
if config_sentry_dsn:function_add_sentry(config_sentry_dsn)
if config_is_prometheus:function_add_prometheus(app)
function_check_required_env(config,["config_postgres_url","config_redis_url","config_key_root","config_key_jwt"])

#middleware
from fastapi import Request,responses
from starlette.background import BackgroundTask
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
   try:
      start=time.time()
      response_type=None
      response=None
      error=None
      api=request.url.path
      request.state.user={}
      request.state.user=await function_token_check(request,request.app.state.config_key_root,request.app.state.config_key_jwt,request.app.state.config_api,function_token_decode)
      if "admin/" in api:await function_check_api_access(request.app.state.config_mode_check_api_access,request,request.app.state.cache_users_api_access,request.app.state.client_postgres,request.app.state.config_api)
      if request.app.state.config_api.get(api,{}).get("is_active_check")==1 and request.state.user:await function_check_is_active(request.app.state.config_mode_check_is_active,request,request.app.state.cache_users_is_active,request.app.state.client_postgres)
      if request.app.state.config_api.get(api,{}).get("ratelimiter_times_sec"):await function_check_ratelimiter(request,request.app.state.client_redis_ratelimiter,request.app.state.config_api)
      if request.query_params.get("is_background")=="1":
         response=await function_api_response_background(request,api_function)
         response_type=1
      elif request.app.state.config_api.get(api,{}).get("cache_sec"):
         response=await function_cache_api_response("get",request,None,request.app.state.client_redis,request.app.state.config_api)
         response_type=2
      if not response:
         response=await api_function(request)
         response_type=3
         if request.app.state.config_api.get(api,{}).get("cache_sec"):
            response=await function_cache_api_response("set",request,response,request.app.state.client_redis,request.app.state.config_api)
            response_type=4
   except Exception as e:
      error=str(e)
      if config_is_traceback:print(traceback.format_exc())
      response=function_return_error(error)
      if request.app.state.config_sentry_dsn:sentry_sdk.capture_exception(e)
      response_type=5
      print(error)
   if request.app.state.config_is_log_api and getattr(request.app.state, "cache_postgres_schema", None) and request.app.state.cache_postgres_schema.get("log_api"):
      obj_log={"response_type":response_type,"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"api_id":request.app.state.config_api.get(api,{}).get("id"),"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"description":error}
      asyncio.create_task(function_log_create_postgres("append",function_object_create_postgres,request.app.state.client_postgres,request.app.state.config_batch_log_api,obj_log))
   return response

#api
from fastapi import Request,responses
import json,time,os,asyncio,uuid

@app.get("/")
async def function_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"}

@app.get("/root/postgres-init")
async def function_api_root_postgres_init(request:Request):
   await function_postgres_schema_init(request.app.state.client_postgres,request.app.state.config_postgres_schema,function_postgres_schema_read)
   return {"status":1,"message":"done"}

@app.delete("/root/postgres-clean")
async def function_api_root_postgres_clean(request:Request):
   await function_postgres_clean(request.app.state.client_postgres,request.app.state.config_postgres_clean)
   return {"status":1,"message":"done"}

@app.post("/root/postgres-export")
async def function_api_root_postgres_export(request:Request):
   param=await function_param_read(request,"body",[["query",1,None,None]])
   stream=function_postgres_query_read_stream(request.app.state.client_postgres_asyncpg_pool,param.get("query"))
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition": "attachment; filename=export_postgres.csv"})

@app.post("/root/postgres-import")
async def function_api_root_postgres_import(request:Request):
   param=await function_param_read(request,"form",[["mode",1,None,None],["table",1,None,None],["file",1,"file",[]]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   if param.get("mode")=="create":output=await function_object_create_postgres(request.app.state.client_postgres,param.get("table"),object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if param.get("mode")=="update":output=await function_object_update_postgres(request.app.state.client_postgres,param.get("table"),object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if param.get("mode")=="delete":output=await function_object_delete_postgres(request.app.state.client_postgres,param.get("table"),object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.post("/root/redis-import")
async def function_api_root_redis_import(request:Request):
   param=await function_param_read(request,"form",[["table",1,None,None],["expiry_sec",0,"int",None]],["file",1,"file",[]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   key_list=[f"{param.get('table')}_{item['id']}" for item in object_list]
   await function_object_create_redis(request.app.state.client_redis,key_list,object_list,param.get("expiry_sec"))
   return {"status":1,"message":"done"}

@app.post("/root/mongodb-import")
async def function_api_root_mongodb_import(request:Request):
   param=await function_param_read(request,"form",[["database",1,None,None],["table",1,None,None],["file",1,"file",[]]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   output=await function_object_create_mongodb(request.app.state.client_mongodb,param.get("database"),param.get("table"),object_list)
   return {"status":1,"message":output}

@app.post("/root/s3-bucket-ops")
async def function_api_root_s3_bucket_ops(request:Request):
   param=await function_param_read(request,"body",[["mode",1,None,None],["bucket",1,None,None]])
   if param.get("mode")=="create":output=await function_s3_bucket_create(request.app.state.config_s3_region_name,request.app.state.client_s3,param.get("bucket"))
   if param.get("mode")=="public":output=await function_s3_bucket_public(request.app.state.client_s3,param.get("bucket"))
   if param.get("mode")=="empty":output=await function_s3_bucket_empty(request.app.state.client_s3_resource,param.get("bucket"))
   if param.get("mode")=="delete":output=await function_s3_bucket_delete(request.app.state.client_s3,param.get("bucket"))
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def function_api_root_s3_url_empty(request:Request):
    param=await function_param_read(request,"body",[["url",1,None,None]])
    for item in param["url"].split("---"):output=await function_s3_url_delete(request.app.state.client_s3_resource,item)
    return {"status":1,"message":output}

@app.get("/root/reset-global")
async def function_api_root_reset_global(request:Request):
    request.app.state.cache_postgres_schema,request.app.state.cache_postgres_column_datatype=await function_postgres_schema_read(request.app.state.client_postgres)
    request.app.state.cache_users_api_access=await function_column_mapping_read(request.app.state.client_postgres_asyncpg,"users","id","api_access",config_limit_cache_users_api_access,0,"split_int")
    request.app.state.cache_users_is_active=await function_column_mapping_read(request.app.state.client_postgres_asyncpg,"users","id","is_active",config_limit_cache_users_api_access,1,None)
    return {"status":1,"message":"done"}
 
@app.post("/auth/signup")
async def function_api_auth_signup(request:Request):
    if request.app.state.config_is_signup==0:return function_return_error("signup disabled")
    param=await function_param_read(request,"body",[["type",1,"int",None],["username",1,None,None],["password",1,None,None]])
    user=await function_auth_signup_username_password(request.app.state.client_postgres,param["type"],param["username"],param["password"])
    token=await function_token_encode(request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list,user)
    return {"status":1,"message":token}
 
@app.post("/auth/signup-bigint")
async def function_api_auth_signup_bigint(request:Request):
    if request.app.state.config_is_signup==0:return function_return_error("signup disabled")
    param=await function_param_read(request,"body",[["type",1,"int",None],["username_bigint",1,None,None],["password_bigint",1,None,None]])
    user=await function_auth_signup_username_password_bigint(request.app.state.client_postgres,param["type"],param["username_bigint"],param["password_bigint"])
    token=await function_token_encode(request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list,user)
    return {"status":1,"message":token}
 
@app.post("/auth/login-password")
async def function_api_auth_login_password(request:Request):
    param=await function_param_read(request,"body",[["type",1,"int",None],["password",1,None,None],["username",1,None,None]])
    token=await function_auth_login_password_username(request.app.state.client_postgres,param["type"],param["password"],param["username"],function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
    return {"status":1,"message":token}

@app.post("/auth/login-password-bigint")
async def function_api_auth_login_password_bigint(request:Request):
    param=await function_param_read(request,"body",[["type",1,"int",None],["password_bigint",1,None,None],["username_bigint",1,None,None]])
    token=await function_auth_login_password_username_bigint(request.app.state.client_postgres,param["type"],param["password_bigint"],param["username_bigint"],function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
    return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def function_api_auth_login_password_email(request:Request):
    param=await function_param_read(request,"body",[["type",1,"int",None],["password",1,None,None],["email",1,None,None]])
    token=await function_auth_login_password_email(request.app.state.client_postgres,param["type"],param["password"],param["email"],function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
    return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def function_api_auth_login_password_mobile(request:Request):
    param=await function_param_read(request,"body",[["type",1,"int",None],["password",1,None,None],["mobile",1,None,None]])
    token=await function_auth_login_password_mobile(request.app.state.client_postgres,param["type"],param["password"],param["mobile"],function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
    return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def function_api_auth_login_otp_email(request:Request):
    param=await function_param_read(request,"body",[["type",1,"int",None],["otp",1,"int",None],["email",1,None,None]])
    token=await function_auth_login_otp_email(request.app.state.client_postgres,param["type"],param["email"],function_otp_verify,param["otp"],function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
    return {"status":1,"message":token}

@app.post("/auth/login-otp-mobile")
async def function_api_auth_login_otp_mobile(request:Request):
    param=await function_param_read(request,"body",[["type",1,"int",None],["otp",1,"int",None],["mobile",1,None,None]])
    token=await function_auth_login_otp_mobile(request.app.state.client_postgres,param["type"],param["mobile"],function_otp_verify,param["otp"],function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
    return {"status":1,"message":token}

@app.post("/auth/login-google")
async def function_api_auth_login_google(request:Request):
    param=await function_param_read(request,"body",[["type",1,"int",None],["google_token",1,None,None]])
    token=await function_auth_login_google(request.app.state.client_postgres,param["type"],param["google_token"],request.app.state.config_google_login_client_id,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
    return {"status":1,"message":token}

@app.get("/my/profile")
async def function_api_my_profile(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   output=await function_read_user_query_count(request.app.state.client_postgres,request.state.user["id"],config_user_count_key)
   asyncio.create_task(function_update_last_active_at(request.app.state.client_postgres,request.state.user["id"]))
   return {"status":1,"message":user|output}

@app.get("/my/api-usage")
async def function_api_my_api_usage(request:Request):
   param=await function_param_read(request,"query",[["days",0,"int",7]])
   object_list=await function_log_api_usage(request.app.state.client_postgres,param["days"],request.state.user["id"])
   return {"status":1,"message":object_list}

@app.get("/my/token-refresh")
async def function_api_my_token_refresh(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   token=await function_token_encode(request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list,user)
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def function_api_my_account_delete(request:Request):
   param=await function_param_read(request,"query",[["mode",1,None,None]])
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   if user["api_access"]:return function_return_error("not allowed as you have api_access")
   await function_delete_user_single(request.app.state.client_postgres,param["mode"],request.state.user["id"])
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def function_api_my_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["is_serialize",0,"int",0],["queue",0,None,None]])
   obj=await function_param_read(request,"body",[])
   obj["created_by_id"]=request.state.user["id"]
   if param["table"] in ["users"]:return function_return_error("table not allowed")
   if len(obj)<=1:return function_return_error("obj issue")
   if any(key in request.app.state.config_column_update_disabled_list for key in obj):return function_return_error("obj key not allowed")
   if not param["queue"]:output=await function_object_create_postgres(request.app.state.client_postgres,param["table"],[obj],param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
   elif param["queue"]:
      payload={"function":"function_object_create_postgres","table":param["table"],"object_list":[obj],"is_serialize":param["is_serialize"]}
      if param["queue"]=="batch":output=await function_object_create_postgres_batch("append",function_object_create_postgres,request.app.state.client_postgres,param["table"],obj,request.app.state.config_batch_object_create,param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
      elif param["queue"].startswith("mongodb"):output=await function_object_create_mongodb(request.app.state.client_mongodb,param["queue"].split('_')[1],param["table"],[obj])
      elif param["queue"]=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",payload)
      elif param["queue"]=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",payload)
      elif param["queue"]=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",payload)
      elif param["queue"]=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_object_create_postgres",[param["table"],[obj],param["is_serialize"]])
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def function_api_my_object_update(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["otp",0,"int",0]])
   obj=await function_param_read(request,"body",[])
   obj["updated_by_id"]=request.state.user["id"]
   if "id" not in obj:return function_return_error("id missing")
   if len(obj)<=2:return function_return_error("obj length issue")
   if any(key in request.app.state.config_column_update_disabled_list for key in obj):return function_return_error("obj key not allowed")
   if param["table"]=="users":
      if obj["id"]!=request.state.user["id"]:return function_return_error("wrong id")
      if any(key in obj and len(obj)!=3 for key in ["password"]):return function_return_error("obj length should be 2")
      if request.app.state.config_is_otp_verify_profile_update and any(key in obj and not param["otp"] for key in ["email","mobile"]):return function_return_error("otp missing")
   if param["otp"]:
      email,mobile=obj.get("email"),obj.get("mobile")
      if email:await function_otp_verify("email",param["otp"],email,request.app.state.client_postgres)
      elif mobile:await function_otp_verify("mobile",param["otp"],mobile,request.app.state.client_postgres)
   if param["table"]=="users":output=await function_object_update_postgres(request.app.state.client_postgres,"users",[obj],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   else:output=await function_object_update_postgres_user(request.app.state.client_postgres,param["table"],[obj],request.state.user["id"],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.get("/my/object-read")
async def function_api_my_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   object_list=await function_object_read_postgres(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":object_list}

@app.get("/my/parent-read")
async def function_api_my_parent_read(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["parent_table",1,None,None],["parent_column",1,None,None],["order",0,None,"id desc"],["limit",0,"int",100],["page",0,"int",1]])
   output=await function_parent_object_read(request.app.state.client_postgres,param["table"],param["parent_column"],param["parent_table"],param["order"],param["limit"],(param["page"]-1)*param["limit"],request.state.user["id"])
   return {"status":1,"message":output}

@app.put("/my/ids-update")
async def function_api_my_ids_update(request:Request):
   param=await function_param_read(request,"body",[["table",1,None,None],["ids",1,None,None],["column",1,None,None],["value",1,None,None]])
   if param["table"] in ["users"]:return function_return_error("table not allowed")
   if param["column"] in request.app.state.config_column_update_disabled_list:return function_return_error("column not allowed")
   await function_update_ids(request.app.state.client_postgres,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def function_api_my_ids_delete(request:Request):
   param=await function_param_read(request,"body",[["table",1,None,None],["ids",1,None,None]])
   if param["table"] in ["users"]:return function_return_error("table not allowed")
   await function_delete_ids(request.app.state.client_postgres,param["table"],param["ids"],request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def function_api_my_object_delete_any(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   if param["table"] in ["users"]:return function_return_error("table not allowed")
   await function_object_delete_postgres_any(request.app.state.client_postgres,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":"done"}

@app.get("/my/message-received")
async def function_api_my_message_received(request:Request):
   param=await function_param_read(request,"query",[["order",0,None,"id desc"],["limit",0,"int",100],["page",0,"int",1],["is_unread",0,None,None]])
   object_list=await function_message_received(request.app.state.client_postgres,request.state.user["id"],param["order"],param["limit"],(param["page"]-1)*param["limit"],param["is_unread"])
   if object_list:asyncio.create_task(function_message_object_mark_read(request.app.state.client_postgres,object_list))
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def function_api_my_message_inbox(request:Request):
   param=await function_param_read(request,"query",[["order",0,None,"id desc"],["limit",0,"int",100],["page",0,"int",1],["is_unread",0,None,None]])
   object_list=await function_message_inbox(request.app.state.client_postgres,request.state.user["id"],param["order"],param["limit"],(param["page"]-1)*param["limit"],param["is_unread"])
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def function_api_my_message_thread(request:Request):
   param=await function_param_read(request,"query",[["user_id",1,"int",None],["order",0,None,"id desc"],["limit",0,"int",100],["page",0,"int",1]])
   object_list=await function_message_thread(request.app.state.client_postgres,request.state.user["id"],param["user_id"],param["order"],param["limit"],(param["page"]-1)*param["limit"])
   asyncio.create_task(function_message_thread_mark_read(request.app.state.client_postgres,request.state.user["id"],param["user_id"]))
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete-bulk")
async def function_api_my_message_delete_bulk(request:Request):
   param=await function_param_read(request,"query",[["mode",1,None,None]])
   if param["mode"]=="all":await function_message_delete_user_all(request.app.state.client_postgres,request.state.user["id"])
   if param["mode"]=="created":await function_message_delete_user_created(request.app.state.client_postgres,request.state.user["id"])
   if param["mode"]=="received":await function_message_delete_user_received(request.app.state.client_postgres,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/message-delete-single")
async def function_api_my_message_delete_single(request:Request):
   param=await function_param_read(request,"query",[["id",1,"int",None]])
   await function_message_delete_user_single(request.app.state.client_postgres,request.state.user["id"],param["id"])
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns")
async def function_api_public_otp_send_mobile_sns(request:Request):
   param=await function_param_read(request,"body",[["mobile",1,None,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   await function_send_mobile_message_sns(request.app.state.client_sns,param["mobile"],str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns-template")
async def function_api_public_otp_send_mobile_sns_template(request:Request):
   param=await function_param_read(request,"body",[["mobile",1,None,None],["message",1,None,None],["template_id",1,None,None],["entity_id",1,None,None],["sender_id",1,None,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   message=param["message"].format(otp=otp)
   await function_send_mobile_message_sns_template(request.app.state.client_sns,param["mobile"],message,param["template_id"],param["entity_id"],param["sender_id"])
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def function_api_public_otp_send_mobile_fast2sms(request:Request):
   param=await function_param_read(request,"body",[["mobile",1,None,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   output=await function_send_mobile_otp_fast2sms(request.app.state.config_fast2sms_url,request.app.state.config_fast2sms_key,param["mobile"],otp)
   return {"status":1,"message":output}

@app.post("/public/otp-send-email-ses")
async def function_api_public_otp_send_email_ses(request:Request):
   param=await function_param_read(request,"body",[["email",1,None,None],["sender_email",1,None,None]])
   otp=await function_otp_generate("email",param["email"],request.app.state.client_postgres)
   await function_send_email_ses(request.app.state.client_ses,param["sender_email"],[param["email"]],"your otp code",str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def function_api_public_otp_send_email_resend(request:Request):
   param=await function_param_read(request,"body",[["email",1,None,None],["sender_email",1,None,None]])
   otp=await function_otp_generate("email",param["email"],request.app.state.client_postgres)
   await function_send_email_resend(request.app.state.config_resend_url,request.app.state.config_resend_key,param["sender_email"],[param["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def function_api_public_otp_verify_email(request:Request):
   param=await function_param_read(request,"body",[["otp",1,"int",None],["email",1,None,None]])
   await function_otp_verify("email",param["otp"],param["email"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def function_api_public_otp_verify_mobile(request:Request):
   param=await function_param_read(request,"body",[["otp",1,"int",None],["mobile",1,None,None]])
   await function_otp_verify("mobile",param["otp"],param["mobile"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def function_api_public_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["is_serialize",0,"int",0]])
   obj=await function_param_read(request,"body",[])
   if param["table"] not in request.app.state.config_public_table_create_list:return function_return_error("table not allowed")
   output=await function_object_create_postgres(request.app.state.client_postgres,param["table"],[obj],param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.get("/public/object-read")
async def function_api_public_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["creator_key",0,None,None]])
   if param["table"] not in request.app.state.config_public_table_read_list:return function_return_error("table not allowed")
   object_list=await function_object_read_postgres(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if object_list and param["creator_key"]:object_list=await function_add_creator_data(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,param["creator_key"],object_list)
   return {"status":1,"message":object_list}

@app.get("/public/info")
async def function_api_public_info(request:Request):
   output={
   "api_list":[route.path for route in request.app.routes],
   "postgres_schema":request.app.state.cache_postgres_schema
   }
   return {"status":1,"message":output}

@app.get("/public/page/{filename}")
async def function_api_public_page(filename:str):
   file_path=os.path.join(".",f"{filename}.html")
   if ".." in filename or "/" in filename:return function_return_error("invalid filename")
   if not os.path.isfile(file_path):return function_return_error("file not found")
   with open(file_path,"r",encoding="utf-8") as file:html_content=file.read()
   return responses.HTMLResponse(content=html_content)

@app.post("/public/jira-worklog-export")
async def function_api_public_jira_worklog_export(request:Request):
   param=await function_param_read(request,"body",[["jira_base_url",1,None,None],["jira_email",1,None,None],["jira_token",1,None,None],["start_date",0,None,None],["end_date",0,None,None]])
   output_path=f"export_jira_worklog_{__import__('time').time():.0f}.csv"
   function_export_jira_worklog(param["jira_base_url"],param["jira_email"],param["jira_token"],param["start_date"],param["end_date"],output_path)
   stream=function_stream_file(output_path)
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment; filename=export_jira_worklog.csv"},background=BackgroundTask(lambda: os.remove(output_path)))

@app.post("/private/file-upload-s3-direct")
async def function_api_private_file_upload_s3_direct(request:Request):
   param=await function_param_read(request,"form",[["bucket",1,None,None],["file_list",1,None,None],["key",0,None,None]])
   key_list=param["key"].split("---") if param["key"] else None
   output=await function_s3_file_upload_direct(request.app.state.config_s3_region_name,request.app.state.client_s3,param["bucket"],key_list,param["file_list"])
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def function_api_private_file_upload_s3_presigned(request:Request):
   param=await function_param_read(request,"body",[["bucket",1,None,None],["key",1,None,None]])
   output=await function_s3_file_upload_presigned(request.app.state.config_s3_region_name,request.app.state.client_s3,param["bucket"],param["key"],1000,100)
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def function_api_admin_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["is_serialize",0,"int",1]])
   obj=await function_param_read(request,"body",[])
   if request.app.state.cache_postgres_schema.get(param["table"]).get("created_by_id"):obj["created_by_id"]=request.state.user["id"]
   output=await function_object_create_postgres(request.app.state.client_postgres,param["table"],[obj],param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def function_api_admin_object_update(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["queue",0,"str",None]])
   obj=await function_param_read(request,"body",[])
   if "id" not in obj:return function_return_error("id missing")
   if len(obj)<=1:return function_return_error("obj length issue")
   if request.app.state.cache_postgres_schema.get(param["table"]).get("updated_by_id"):obj["updated_by_id"]=request.state.user["id"]
   if not param["queue"]:output=await function_object_update_postgres(request.app.state.client_postgres,param["table"],[obj],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   elif param["queue"]=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_object_update_postgres",[param["table"],[obj],1])
   elif param["queue"]=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def function_api_admin_ids_update(request:Request):
   param=await function_param_read(request,"body",[["table",1,None,None],["ids",1,None,None],["column",1,None,None],["value",1,None,None]])
   await function_update_ids(request.app.state.client_postgres,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],None)
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def function_api_admin_ids_delete(request:Request):
   param=await function_param_read(request,"body",[["table",1,None,None],["ids",1,None,None]])
   await function_delete_ids(request.app.state.client_postgres,param["table"],param["ids"],None)
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
async def function_api_admin_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None]])
   obj=await function_param_read(request,"query",[])
   object_list=await function_object_read_postgres(request.app.state.client_postgres,param["table"],obj,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":object_list}

@app.post("/admin/postgres-query-runner")
async def function_api_admin_postgres_query_runner(request:Request):
   param=await function_param_read(request,"body",[["query",1,None,None],["queue",0,"str",None]])
   if not param["queue"]:output=await function_postgres_query_runner(request.app.state.client_postgres,param["query"],request.state.user["id"])
   elif param["queue"]=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_postgres_query_runner",[param["query"],request.state.user["id"]])
   elif param["queue"]=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   elif param["queue"]=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   elif param["queue"]=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   if False:request.app.state.client_posthog.capture(distinct_id=request.state.user["id"],event="postgres_query_runner",properties={"query":param["query"]})
   return {"status":1,"message":output}

@app.post("/admin/postgres-export")
async def function_api_root_postgres_export(request:Request):
   param=await function_param_read(request,"body",[["query",1,None,None]])
   stream=function_postgres_query_read_stream(request.app.state.client_postgres_asyncpg_pool,param["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment; filename=export_postgres.csv"})

#server start
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_server_start(app))
   except KeyboardInterrupt:print("exit")