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
config_redis_pubsub_url=config.get("config_redis_pubsub_url")
config_kafka_url=config.get("config_kafka_url")
config_kafka_username=config.get("config_kafka_username")
config_kafka_password=config.get("config_kafka_password")
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
config_is_otp_verify=int(config.get("config_is_otp_verify",1))
config_batch_log_api=int(config.get("config_batch_log_api",10))
config_is_log_api=int(config.get("config_is_log_api",1))
config_batch_object_create=int(config.get("config_batch_object_create",10))
config_limit_cache_users_api_access=int(config.get("config_limit_cache_users_api_access",1000))
config_limit_cache_users_is_active=int(config.get("config_limit_cache_users_is_active",0))
config_token_user_key_list=config.get("config_token_user_key_list","id,type,is_active,api_access").split(",")
config_column_update_disabled_list=config.get("config_column_update_disabled_list","is_active,is_verified,api_access").split(",")
config_public_table_create_list=config.get("config_public_table_create_list","test").split(",")
config_public_table_read_list=config.get("config_public_table_read_list","test").split(",")
config_cors_origin_list=config.get("config_cors_origin_list","*").split(",")
config_cors_method_list=config.get("config_cors_method_list","*").split(",")
config_cors_headers_list=config.get("config_cors_headers_list","*").split(",")
config_cors_allow_credentials=config.get("config_cors_allow_credentials",False)
config_is_prometheus=int(config.get("config_is_prometheus",0))
config_api=config.get("config_api",{})
config_postgres_schema=config.get("config_postgres_schema",{})

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
      client_celery_producer=await function_client_read_celery_producer(config_celery_broker_url) if config_celery_broker_url else None
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
   except Exception as e:
      print(str(e))
      print(traceback.format_exc())

#app
app=function_fastapi_app_read(True,lifespan)
function_add_cors(app,config_cors_origin_list,config_cors_method_list,config_cors_headers_list,config_cors_allow_credentials)
function_add_router(app,"router")
if config_sentry_dsn:function_add_sentry(config_sentry_dsn)
if config_is_prometheus:function_add_prometheus(app)

#middleware
from fastapi import Request,responses
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
   try:
      start=time.time()
      type=None
      response=None
      error=None
      api=request.url.path
      request.state.user={}
      request.state.user=await function_token_check(request,config_key_root,config_key_jwt,config_api,function_token_decode)
      if "admin/" in api:await function_check_api_access(config_mode_check_api_access,request,request.app.state.cache_users_api_access,request.app.state.client_postgres,config_api)
      if config_api.get(api,{}).get("is_active_check")==1 and request.state.user:await function_check_is_active(config_mode_check_is_active,request,request.app.state.cache_users_is_active,request.app.state.client_postgres)
      if config_api.get(api,{}).get("ratelimiter_times_sec"):await function_check_ratelimiter(request,request.app.state.client_redis_ratelimiter,config_api)
      if request.query_params.get("is_background")=="1":
         response=await function_api_response_background(request,api_function)
         type=1
      elif config_api.get(api,{}).get("cache_sec"):
         response=await function_cache_api_response("get",request,None,request.app.state.client_redis,config_api)
         type=2
      if not response:
         response=await api_function(request)
         type=3
         if config_api.get(api,{}).get("cache_sec"):
            response=await function_cache_api_response("set",request,response,request.app.state.client_redis,config_api)
            type=4
   except Exception as e:
      error=str(e)
      print(traceback.format_exc())
      response=function_return_error(error)
      if config_sentry_dsn:sentry_sdk.capture_exception(e)
      type=5
   if config_is_log_api and getattr(request.app.state, "cache_postgres_schema", None) and request.app.state.cache_postgres_schema.get("log_api"):
      object={"type":type,"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"description":error}
      asyncio.create_task(function_log_create_postgres(function_object_create_postgres,request.app.state.client_postgres,config_batch_log_api,object))
   return response

#api
from fastapi import Request,responses
import json,time,os,asyncio

@app.get("/")
async def function_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"}

@app.get("/root/postgres-init")
async def function_api_root_postgres_init(request:Request):
   await function_postgres_schema_init(request.app.state.client_postgres,request.app.state.config_postgres_schema,function_postgres_schema_read)
   return {"status":1,"message":"done"}

@app.post("/root/postgres-export")
async def function_api_root_postgres_export(request:Request):
   object,[query]=await function_param_read("body",request,["query"],[])
   return responses.StreamingResponse(function_postgres_stream(request.app.state.client_postgres_asyncpg_pool,query),media_type="text/csv",headers={"Content-Disposition": "attachment; filename=query_result.csv"})

@app.post("/root/postgres-import")
async def function_api_root_postgres_import(request:Request):
   object,[mode,table,file_list]=await function_param_read("form",request,["mode","table","file_list"],[])
   object_list=await function_file_to_object_list(file_list[-1])
   if mode=="create":output=await function_object_create_postgres(request.app.state.client_postgres,table,object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if mode=="update":output=await function_object_update_postgres(request.app.state.client_postgres,table,object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if mode=="delete":output=await function_object_delete_postgres(request.app.state.client_postgres,table,object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.post("/root/redis-import")
async def function_api_root_redis_import(request:Request):
   object,[table,file_list,expiry_sec]=await function_param_read("form",request,["table","file_list"],["expiry_sec"])
   object_list=await function_file_to_object_list(file_list[-1])
   key_list=[f"{table}_{item['id']}" for item in object_list]
   await function_object_create_redis(request.app.state.client_redis,key_list,object_list,expiry_sec)
   return {"status":1,"message":"done"}

@app.post("/root/mongodb-import")
async def function_api_root_mongodb_import(request:Request):
   object,[database,table,file_list]=await function_param_read("form",request,["database","table","file_list"],[])
   object_list=await function_file_to_object_list(file_list[-1])
   output=await function_object_create_mongodb(request.app.state.client_mongodb,database,table,object_list)
   return {"status":1,"message":output}

@app.post("/root/s3-bucket-ops")
async def function_api_root_s3_bucket_ops(request:Request):
   object,[mode,bucket]=await function_param_read("body",request,["mode","bucket"],[])
   if mode=="create":output=await function_s3_bucket_create(request.app.state.config_s3_region_name,request.app.state.client_s3,bucket)
   if mode=="public":output=await function_s3_bucket_public(request.app.state.client_s3,bucket)
   if mode=="empty":output=await function_s3_bucket_empty(request.app.state.client_s3_resource,bucket)
   if mode=="delete":output=await function_s3_bucket_delete(request.app.state.client_s3,bucket)
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def function_api_root_s3_url_empty(request:Request):
   object,[url]=await function_param_read("body",request,["url"],[])
   for item in url.split("---"):output=await function_s3_url_delete(request.app.state.client_s3_resource,item)
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
   object,[type,username,password]=await function_param_read("body",request,["type","username","password"],[])
   user=await function_auth_signup_username_password(request.app.state.client_postgres,type,username,password)
   token=await function_token_encode(request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list,user)
   return {"status":1,"message":token}

@app.post("/auth/signup-bigint")
async def function_api_auth_signup_bigint(request:Request):
   if request.app.state.config_is_signup==0:return function_return_error("signup disabled")
   object,[type,username_bigint,password_bigint]=await function_param_read("body",request,["type","username_bigint","password_bigint"],[])
   user=await function_auth_signup_username_password_bigint(request.app.state.client_postgres,type,username_bigint,password_bigint)
   token=await function_token_encode(request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list,user)
   return {"status":1,"message":token}

@app.post("/auth/login-password")
async def function_api_auth_login_password(request:Request):
   object,[type,password,username]=await function_param_read("body",request,["type","password","username"],[])
   token=await function_auth_login_password_username(request.app.state.client_postgres,type,password,username,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
   return {"status":1,"message":token}

@app.post("/auth/login-password-bigint")
async def function_api_auth_login_password_bigint(request:Request):
   object,[type,password_bigint,username_bigint]=await function_param_read("body",request,["type","password_bigint","username_bigint"],[])
   token=await function_auth_login_password_username_bigint(request.app.state.client_postgres,type,password_bigint,username_bigint,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def function_api_auth_login_password_email(request:Request):
   object,[type,password,email]=await function_param_read("body",request,["type","password","email"],[])
   token=await function_auth_login_password_email(request.app.state.client_postgres,type,password,email,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def function_api_auth_login_password_mobile(request:Request):
   object,[type,password,mobile]=await function_param_read("body",request,["type","password","mobile"],[])
   token=await function_auth_login_password_mobile(request.app.state.client_postgres,type,password,mobile,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def function_api_auth_login_otp_email(request:Request):
   object,[type,otp,email]=await function_param_read("body",request,["type","otp","email"],[])
   token=await function_auth_login_otp_email(request.app.state.client_postgres,type,email,function_otp_verify,otp,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-mobile")
async def function_api_auth_login_otp_mobile(request:Request):
   object,[type,otp,mobile]=await function_param_read("body",request,["type","otp","mobile"],[])
   token=await function_auth_login_otp_mobile(request.app.state.client_postgres,type,mobile,function_otp_verify,otp,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
   return {"status":1,"message":token}

@app.post("/auth/login-google")
async def function_api_auth_login_google(request:Request):
   object,[type,google_token]=await function_param_read("body",request,["type","google_token"],[])
   token=await function_auth_login_google(request.app.state.client_postgres,type,google_token,request.app.state.config_google_login_client_id,function_token_encode,request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list)
   return {"status":1,"message":token}

@app.get("/my/profile")
async def function_api_my_profile(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   asyncio.create_task(function_update_last_active_at(request.app.state.client_postgres,request.state.user["id"]))
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def function_api_my_token_refresh(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   token=await function_token_encode(request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list,user)
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def function_api_my_account_delete(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   if user["api_access"]:return function_return_error("not allowed as you have api_access")
   await function_delete_user_single(request.app.state.client_postgres,mode,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def function_api_my_object_create(request:Request):
   object_1,[table,is_serialize,queue]=await function_param_read("query",request,["table"],["is_serialize","queue"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 0
   object["created_by_id"]=request.state.user["id"]
   if table in ["users"]:return function_return_error("table not allowed")
   if len(object)<=1:return function_return_error ("object issue")
   if any(key in request.app.state.config_column_update_disabled_list for key in object):return function_return_error(" object key not allowed")
   if not queue:output=await function_object_create_postgres(request.app.state.client_postgres,table,[object],is_serialize,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   elif queue:
      payload={"function":"function_object_create_postgres","table":table,"object_list":[object],"is_serialize":is_serialize}
      if queue=="batch":output=await function_object_create_postgres_batch(function_object_create_postgres,request.app.state.client_postgres,table,object,request.app.state.config_batch_object_create,is_serialize,function_object_serialize,request.app.state.cache_postgres_column_datatype)
      elif queue.startswith("mongodb"):output=await function_object_create_mongodb(request.app.state.client_mongodb,queue.split('_')[1],table,[object])
      elif queue=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",payload)
      elif queue=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",payload)
      elif queue=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",payload)
      elif queue=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_object_create_postgres",[table,[object],is_serialize])
   return {"status":1,"message":output}

@app.get("/my/object-read")
async def function_api_my_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   object_list=await function_object_read_postgres(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,table,object,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":object_list}

@app.get("/my/parent-read")
async def function_api_my_parent_read(request:Request):
   object,[table,parent_table,parent_column,order,limit,page]=await function_param_read("query",request,["table","parent_table","parent_column"],["order","limit","page"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   output=await function_parent_object_read(request.app.state.client_postgres,table,parent_column,parent_table,order,limit,(page-1)*limit,request.state.user["id"])
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def function_api_my_object_update(request:Request):
   object_1,[table,otp]=await function_param_read("query",request,["table"],["otp"])
   object,[]=await function_param_read("body",request,[],[])
   object["updated_by_id"]=request.state.user["id"]
   if "id" not in object:return function_return_error ("id missing")
   if len(object)<=2:return function_return_error ("object length issue")
   if any(key in request.app.state.config_column_update_disabled_list for key in object):return function_return_error(" object key not allowed")
   if table=="users":
      if object["id"]!=request.state.user["id"]:return function_return_error ("wrong id")
      if any(key in object and len(object)!=3 for key in ["password"]):return function_return_error("object length should be 2")
      if request.app.state.config_is_otp_verify and any(key in object and not otp for key in ["email","mobile"]):return function_return_error("otp missing")
   if otp:
      email,mobile=object.get("email"),object.get("mobile")
      if email:await function_otp_verify("email",otp,email,request.app.state.client_postgres)
      elif mobile:await function_otp_verify("mobile",otp,mobile,request.app.state.client_postgres)
   if table=="users":output=await function_object_update_postgres(request.app.state.client_postgres,"users",[object],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   else:output=await function_object_update_postgres_user(request.app.state.client_postgres,table,[object],request.state.user["id"],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.put("/my/ids-update")
async def function_api_my_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   if table in ["users"]:return function_return_error("table not allowed")
   if column in request.app.state.config_column_update_disabled_list:return function_return_error("column not allowed")
   await function_update_ids(request.app.state.client_postgres,table,ids,column,value,request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def function_api_my_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   if table in ["users"]:return function_return_error("table not allowed")
   await function_delete_ids(request.app.state.client_postgres,table,ids,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def function_api_my_object_delete_any(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   if table in ["users"]:return function_return_error("table not allowed")
   await function_object_delete_postgres_any(request.app.state.client_postgres,table,object,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":"done"}

@app.get("/my/message-received")
async def function_api_my_message_received(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_received(request.app.state.client_postgres,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   if object_list:asyncio.create_task(function_message_object_mark_read(request.app.state.client_postgres,object_list))
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def function_api_my_message_inbox(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_inbox(request.app.state.client_postgres,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def function_api_my_message_thread(request:Request):
   object,[user_id,order,limit,page]=await function_param_read("query",request,["user_id"],["order","limit","page"])
   user_id=int(user_id)
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_thread(request.app.state.client_postgres,request.state.user["id"],user_id,order,limit,(page-1)*limit)
   asyncio.create_task(function_message_thread_mark_read(request.app.state.client_postgres,request.state.user["id"],user_id))
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete-bulk")
async def function_api_my_message_delete_bulk(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   if mode=="all":await function_message_delete_user_all(request.app.state.client_postgres,request.state.user["id"])
   if mode=="created":await function_message_delete_user_created(request.app.state.client_postgres,request.state.user["id"])
   if mode=="received":await function_message_delete_user_received(request.app.state.client_postgres,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/message-delete-single")
async def function_api_my_message_delete_single(request:Request):
   object,[id]=await function_param_read("query",request,["id"],[])
   await function_message_delete_user_single(request.app.state.client_postgres,request.state.user["id"],int(id))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns")
async def function_api_public_otp_send_mobile_sns(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_otp_generate("mobile",mobile,request.app.state.client_postgres)
   await function_send_mobile_message_sns(request.app.state.client_sns,mobile,str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns-template")
async def function_api_public_otp_send_mobile_sns_template(request:Request):
   object,[mobile,message,template_id,entity_id,sender_id]=await function_param_read("body",request,["mobile","message","template_id","entity_id","sender_id"],[])
   otp=await function_otp_generate("mobile",mobile,request.app.state.client_postgres)
   await function_send_mobile_message_sns_template(request.app.state.client_sns,mobile,message,template_id,entity_id,sender_id)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def function_api_public_otp_send_mobile_fast2sms(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_otp_generate("mobile",mobile,request.app.state.client_postgres)
   output=await function_send_mobile_otp_fast2sms(request.app.state.config_fast2sms_url,request.app.state.config_fast2sms_key,mobile,otp)
   return {"status":1,"message":output}

@app.post("/public/otp-send-email-ses")
async def function_api_public_otp_send_email_ses(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_otp_generate("email",email,request.app.state.client_postgres)
   await function_send_email_ses(request.app.state.client_ses,sender_email,[email],"your otp code",str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def function_api_public_otp_send_email_resend(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_otp_generate("email",email,request.app.state.client_postgres)
   await function_send_email_resend(request.app.state.config_resend_url,request.app.state.config_resend_key,sender_email,[email],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def function_api_public_otp_verify_email(request:Request):
   object,[otp,email]=await function_param_read("body",request,["otp","email"],[])
   await function_otp_verify("email",otp,email,request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def function_api_public_otp_verify_mobile(request:Request):
   object,[otp,mobile]=await function_param_read("body",request,["otp","mobile"],[])
   await function_otp_verify("mobile",otp,mobile,request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def function_api_public_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 0
   if table not in request.app.state.config_public_table_create_list:return function_return_error("table not allowed")
   output=await function_object_create_postgres(request.app.state.client_postgres,table,[object],is_serialize,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.get("/public/object-read")
async def function_api_public_object_read(request:Request):
   object,[table,creator_key]=await function_param_read("query",request,["table"],["creator_key"])
   if table not in request.app.state.config_public_table_read_list:return function_return_error("table not allowed")
   object_list=await function_object_read_postgres(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,table,object,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if object_list and creator_key:object_list=await function_add_creator_data(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,creator_key,object_list)
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
   if not os.path.isfile(file_path):return function_return_error ("file not found")
   with open(file_path, "r", encoding="utf-8") as file:html_content=file.read()
   return responses.HTMLResponse(content=html_content)

@app.post("/private/file-upload-s3-direct")
async def function_api_private_file_upload_s3_direct(request:Request):
   object,[bucket,file_list,key]=await function_param_read("form",request,["bucket","file_list"],["key"])
   key_list=key.split("---") if key else None
   output=await function_s3_file_upload_direct(request.app.state.config_s3_region_name,request.app.state.client_s3,bucket,key_list,file_list)
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def function_api_private_file_upload_s3_presigned(request:Request):
   object,[bucket,key]=await function_param_read("body",request,["bucket","key"],[])
   output=await function_s3_file_upload_presigned(request.app.state.config_s3_region_name,request.app.state.client_s3,bucket,key,1000,100)
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def function_api_admin_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 1
   if request.app.state.cache_postgres_schema.get(table).get("created_by_id"):object["created_by_id"]=request.state.user["id"]
   output=await function_object_create_postgres(request.app.state.client_postgres,table,[object],is_serialize,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def function_api_admin_object_update(request:Request):
   object_1,[table,queue]=await function_param_read("query",request,["table"],["queue"])
   object,[]=await function_param_read("body",request,[],[])
   if "id" not in object:return function_return_error ("id missing")
   if len(object)<=1:return function_return_error ("object length issue")
   if request.app.state.cache_postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   if not queue:output=await function_object_update_postgres(request.app.state.client_postgres,table,[object],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   elif queue=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_object_update_postgres",[table,[object],1])
   elif queue=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_object_update_postgres","table":table,"object_list":[object],"is_serialize":1})
   elif queue=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_object_update_postgres","table":table,"object_list":[object],"is_serialize":1})
   elif queue=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_object_update_postgres","table":table,"object_list":[object],"is_serialize":1})
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def function_api_admin_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   await function_update_ids(request.app.state.client_postgres,table,ids,column,value,request.state.user["id"],None)
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def function_api_admin_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   await function_delete_ids(request.app.state.client_postgres,table,ids,None)
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
async def function_api_admin_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object_list=await function_object_read_postgres(request.app.state.client_postgres,table,object,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":object_list}

@app.post("/admin/postgres-query-runner")
async def function_api_admin_postgres_query_runner(request:Request):
   object,[query,queue]=await function_param_read("body",request,["query"],["queue"])
   if not queue:output=await function_postgres_query_runner(request.app.state.client_postgres,query,request.state.user["id"])
   elif queue=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_postgres_query_runner",[query,request.state.user["id"]])
   elif queue=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_postgres_query_runner","query":query,"user_id":request.state.user["id"]})
   elif queue=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_postgres_query_runner","query":query,"user_id":request.state.user["id"]})
   elif queue=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_postgres_query_runner","query":query,"user_id":request.state.user["id"]})
   if False:request.app.state.client_posthog.capture(distinct_id=request.state.user["id"],event="postgres_query_runner",properties={"query":query})
   return {"status":1,"message":output}

#server start
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_server_start(app))
   except KeyboardInterrupt:print("exit")