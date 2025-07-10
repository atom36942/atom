#function
from function import *

#env
env=function_load_env(".env")

#config
config_postgres_url=env.get("config_postgres_url")
config_postgres_url_read=env.get("config_postgres_url_read")
config_redis_url=env.get("config_redis_url")
config_key_root=env.get("config_key_root")
config_key_jwt=env.get("config_key_jwt")
config_sentry_dsn=env.get("config_sentry_dsn")
config_mongodb_url=env.get("config_mongodb_url")
config_rabbitmq_url=env.get("config_rabbitmq_url")
config_lavinmq_url=env.get("config_lavinmq_url")
config_kafka_url=env.get("config_kafka_url")
config_kafka_path_cafile=env.get("config_kafka_path_cafile")
config_kafka_path_certfile=env.get("config_kafka_path_certfile")
config_kafka_path_keyfile=env.get("config_kafka_path_keyfile")
config_aws_access_key_id=env.get("config_aws_access_key_id")
config_aws_secret_access_key=env.get("config_aws_secret_access_key")
config_s3_region_name=env.get("config_s3_region_name")
config_sns_region_name=env.get("config_sns_region_name")
config_ses_region_name=env.get("config_ses_region_name")
config_google_login_client_id=env.get("config_google_login_client_id")
config_fast2sms_key=env.get("config_fast2sms_key")
config_fast2sms_url=env.get("config_fast2sms_url")
config_resend_key=env.get("config_resend_key")
config_resend_url=env.get("config_resend_url")
config_posthog_project_key=env.get("config_posthog_project_key")
config_posthog_project_host=env.get("config_posthog_project_host")
config_openai_key=env.get("config_openai_key")
config_token_expire_sec=int(env.get("config_token_expire_sec",365*24*60*60))
config_is_signup=int(env.get("config_is_signup",1))
config_limit_log_api_batch=int(env.get("config_limit_log_api_batch",10))
config_limit_cache_users_api_access=int(env.get("config_limit_cache_users_api_access",1000))
config_limit_cache_users_is_active=int(env.get("config_limit_cache_users_is_active",0))
config_channel_name=env.get("config_channel_name","ch1")
config_mode_check_api_access=env.get("config_mode_check_api_access","cache")
config_mode_check_is_active=env.get("config_mode_check_is_active","token")
config_super_user_id_list=[int(item) for item in env.get("config_super_user_id_list","1").split(",")]
config_column_disabled_non_admin_list=env.get("config_column_disabled_non_admin_list","is_active,is_verified,api_access").split(",")
config_table_allowed_public_create_list=env.get("config_table_allowed_public_create_list","test").split(",")
config_table_allowed_public_read_list=env.get("config_table_allowed_public_read_list","test").split(",")
config_router_list=env.get("config_router_list").split(",") if env.get("config_router_list") else []
config_api={
"/admin/object-create":{"id":1,"ratelimiter_times_sec":[1,1]},
"/admin/object-update":{"id":2},
"/admin/ids-update":{"id":3},
"/admin/ids-delete":{"id":4}, 
"/admin/object-read":{"id":5,"cache_sec":["redis",100]},
"/admin/db-runner":{"id":6,"is_active_check":1},
"/public/info":{"id":7,"cache_sec":["inmemory",60],"ratelimiter_times_sec":[1,1]},
"/my/parent-read":{"id":8,"cache_sec":["redis",100]},
"/test":{"is_token":0}
}
config_postgres_schema={
"table":{
"test":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-bigint-0-btree",
"title-text-0-0",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0",
"rating-numeric(10,3)-0-0",
"remark-text-0-btree,gin",
"location-geography(POINT)-0-gist",
"metadata-jsonb-0-gin"
],
"log_api":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"type-bigint-0-btree",
"ip_address-text-0-0",
"api-text-0-btree,gin",
"method-text-0-0",
"query_param-text-0-0",
"status_code-smallint-0-0",
"response_time_ms-numeric(1000,3)-0-0",
"description-text-0-0"
],
"otp":[
"created_at-timestamptz-0-brin",
"otp-integer-1-0",
"email-text-0-btree",
"mobile-text-0-btree"
],
"log_password":[
"created_at-timestamptz-0-0",
"user_id-bigint-0-0",
"password-text-0-0"
],
"users":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-bigint-1-btree",
"username-text-0-btree",
"password-text-0-btree",
"google_id-text-0-btree",
"google_data-jsonb-0-0",
"email-text-0-btree",
"mobile-text-0-btree",
"api_access-text-0-0",
"last_active_at-timestamptz-0-0",
"username_bigint-bigint-0-btree",
"password_bigint-bigint-0-btree"
],
"message":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"user_id-bigint-1-btree",
"description-text-1-0",
"is_read-smallint-0-btree"
],
"report_user":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"user_id-bigint-1-btree"
]
},
"query":{
"delete_disable_bulk_users":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"check_username":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"unique_1":"alter table users add constraint constraint_unique_users_type_username unique (type,username);",
"unique_2":"alter table users add constraint constraint_unique_users_type_email unique (type,email);",
"unique_3":"alter table users add constraint constraint_unique_users_type_mobile unique (type,mobile);",
"unique_4":"alter table users add constraint constraint_unique_users_type_google_id unique (type,google_id);",
"unique_5":"alter table report_user add constraint constraint_unique_report_user unique (created_by_id,user_id);",
"unique_6":"alter table users add constraint constraint_unique_users_type_username_bigint unique (type,username_bigint);",
}
}

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import traceback
@asynccontextmanager
async def lifespan(app:FastAPI):
   try:
      #client init
      client_postgres=await function_client_read_postgres(config_postgres_url) if config_postgres_url else None
      client_postgres_asyncpg,client_postgres_asyncpg_pool=await function_client_read_postgres_asyncpg(config_postgres_url) if config_postgres_url else None
      client_postgres_read=await function_client_read_postgres(config_postgres_url_read) if config_postgres_url_read else None
      client_redis=await function_client_read_redis(config_redis_url) if config_redis_url else None
      client_mongodb=await function_client_read_mongodb(config_mongodb_url) if config_mongodb_url else None
      client_s3,client_s3_resource=(await function_client_read_s3(config_s3_region_name,config_aws_access_key_id,config_aws_secret_access_key)) if config_s3_region_name else (None, None)
      client_sns=await function_client_read_sns(config_sns_region_name,config_aws_access_key_id,config_aws_secret_access_key) if config_sns_region_name else None
      client_ses=await function_client_read_ses(config_ses_region_name,config_aws_access_key_id,config_aws_secret_access_key) if config_ses_region_name else None
      client_openai=function_client_read_openai(config_openai_key) if config_openai_key else None
      client_kafka_producer=await function_client_read_kafka_producer(config_kafka_url,config_kafka_path_cafile,config_kafka_path_certfile,config_kafka_path_keyfile) if config_kafka_url else None
      client_rabbitmq,client_rabbitmq_channel=await function_client_read_rabbitmq(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
      client_lavinmq,client_lavinmq_channel=await function_client_read_lavinmq(config_lavinmq_url) if config_lavinmq_url else (None, None)
      client_celery_producer=await function_client_read_celery_producer(config_redis_url) if config_redis_url else None
      client_posthog=await function_client_read_posthog(config_posthog_project_key,config_posthog_project_host)
      #cache init
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres) if client_postgres else (None, None)
      cache_users_api_access=await function_cache_users_api_access_read(config_limit_cache_users_api_access,client_postgres_asyncpg) if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("api_access") else {}
      cache_users_is_active=await function_cache_users_is_active_read(config_limit_cache_users_is_active,client_postgres_asyncpg) if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("is_active") else {}
      #app state set
      function_app_add_state_lifespan(locals(),app)
      #app shutdown
      yield
      if client_postgres:await client_postgres.disconnect()
      if client_postgres_asyncpg:await client_postgres_asyncpg.close()
      if client_postgres_asyncpg_pool:await client_postgres_asyncpg_pool.close()
      if client_postgres_read:await client_postgres_read.close()
      if client_redis:await client_redis.aclose()
      if client_mongodb:await client_mongodb.close()
      if client_kafka_producer:await client_kafka_producer.stop()
      if client_rabbitmq_channel and not client_rabbitmq_channel.is_closed:await client_rabbitmq_channel.close()
      if client_rabbitmq and not client_rabbitmq.is_closed:await client_rabbitmq.close()
      if client_lavinmq_channel and not client_lavinmq_channel.is_closed:await client_lavinmq_channel.close()
      if client_lavinmq and not client_lavinmq.is_closed:await client_lavinmq.close()
      if client_posthog:client_posthog.flush()
   except Exception as e:
      print(str(e))
      print(traceback.format_exc())
   
#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan,debug=True)
function_app_add_cors(app)
function_app_add_router(app,config_router_list)
if config_sentry_dsn:function_app_add_sentry(config_sentry_dsn)
if True:function_app_add_prometheus(app)

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
      if config_api.get(api,{}).get("ratelimiter_times_sec"):await function_check_ratelimiter(request,request.app.state.client_redis,config_api)
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
   if request.app.state.cache_postgres_schema.get("log_api"):
      object={"type":type,"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"description":error}
      asyncio.create_task(function_postgres_log_create(object,config_limit_log_api_batch,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_create,function_postgres_object_serialize))
   return response

#api
from fastapi import Request,responses
import json,time,os,asyncio,sys

@app.get("/")
async def index():
   return {"status":1,"message":"welcome to atom"}

@app.get("/root/postgres-init")
async def root_postgres_init(request:Request):
   await function_postgres_schema_init(request.app.state.client_postgres,config_postgres_schema,function_postgres_schema_read)
   return {"status":1,"message":"done"}

@app.post("/root/postgres-csv-export")
async def root_postgres_csv_export(request:Request):
   object,[query]=await function_param_read("body",request,["query"],[])
   return responses.StreamingResponse(function_stream_csv_from_query(query,request.app.state.client_postgres_asyncpg_pool),media_type="text/csv",headers={"Content-Disposition": "attachment; filename=query_result.csv"})

@app.post("/root/postgres-csv-import")
async def root_postgres_csv_import(request:Request):
   object,[mode,table,file_list]=await function_param_read("form",request,["mode","table","file_list"],[])
   object_list=await function_file_to_object_list(file_list[-1])
   if mode=="create":output=await function_postgres_object_create(table,object_list,1,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   if mode=="update":output=await function_postgres_object_update(table,object_list,1,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   if mode=="delete":output=await function_postgres_object_delete(table,object_list,1,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   return {"status":1,"message":output}

@app.post("/root/redis-csv-import")
async def root_redis_csv_import(request:Request):
   object,[table,file_list,expiry_sec]=await function_param_read("form",request,["table","file_list"],["expiry_sec"])
   object_list=await function_file_to_object_list(file_list[-1])
   await function_redis_object_create(table,object_list,expiry_sec,request.app.state.client_redis)
   return {"status":1,"message":"done"}

@app.post("/root/s3-bucket-ops")
async def root_s3_bucket_ops(request:Request):
   object,[mode,bucket]=await function_param_read("body",request,["mode","bucket"],[])
   if mode=="create":output=await function_s3_bucket_create(bucket,request.app.state.client_s3,config_s3_region_name)
   if mode=="public":output=await function_s3_bucket_public(bucket,request.app.state.client_s3)
   if mode=="empty":output=await function_s3_bucket_empty(bucket,request.app.state.client_s3_resource)
   if mode=="delete":output=await function_s3_bucket_delete(bucket,request.app.state.client_s3)
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   object,[url]=await function_param_read("body",request,["url"],[])
   for item in url.split("---"):output=await function_s3_url_delete(item,request.app.state.client_s3_resource)
   return {"status":1,"message":output}

@app.get("/root/reset-global")
async def root_reset_global(request:Request):
   request.app.state.cache_postgres_schema,request.app.state.cache_postgres_column_datatype=await function_postgres_schema_read(request.app.state.client_postgres)
   request.app.state.cache_users_api_access=await function_cache_users_api_access_read(config_limit_cache_users_api_access,request.app.state.client_postgres_asyncpg)
   request.app.state.cache_users_is_active=await function_cache_users_is_active_read(config_limit_cache_users_is_active,request.app.state.client_postgres_asyncpg) 
   return {"status":1,"message":"done"}
   
@app.post("/auth/signup")
async def auth_signup(request:Request):
   if config_is_signup==0:return function_return_error("signup disabled")
   object,[type,username,password]=await function_param_read("body",request,["type","username","password"],[])
   user=await function_signup_username_password(type,username,password,request.app.state.client_postgres)
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return {"status":1,"message":token}

@app.post("/auth/signup-bigint")
async def auth_signup_bigint(request:Request):
   if config_is_signup==0:return function_return_error("signup disabled")
   object,[type,username,password]=await function_param_read("body",request,["type","username","password"],[])
   user=await function_signup_username_password_bigint(type,username,password,request.app.state.client_postgres)
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return {"status":1,"message":token}

@app.post("/auth/login-password")
async def auth_login_password(request:Request):
   object,[type,password,username]=await function_param_read("body",request,["type","password","username"],[])
   token=await function_login_password_username(type,password,username,request.app.state.client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode)
   return {"status":1,"message":token}

@app.post("/auth/login-password-bigint")
async def auth_login_password_bigint(request:Request):
   object,[type,password,username]=await function_param_read("body",request,["type","password","username"],[])
   token=await function_login_password_username_bigint(type,password,username,request.app.state.client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode)
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   object,[type,password,email]=await function_param_read("body",request,["type","password","email"],[])
   token=await function_login_password_email(type,password,email,request.app.state.client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode)
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   object,[type,password,mobile]=await function_param_read("body",request,["type","password","mobile"],[])
   token=await function_login_password_mobile(type,password,mobile,request.app.state.client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def auth_login_otp_email(request:Request):
   object,[type,otp,email]=await function_param_read("body",request,["type","otp","email"],[])
   token=await function_login_otp_email(type,email,otp,request.app.state.client_postgres,config_key_jwt,config_token_expire_sec,function_otp_verify,function_token_encode)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-mobile")
async def auth_login_otp_mobile(request:Request):
   object,[type,otp,mobile]=await function_param_read("body",request,["type","otp","mobile"],[])
   token=await function_login_otp_mobile(type,mobile,otp,request.app.state.client_postgres,config_key_jwt,config_token_expire_sec,function_otp_verify,function_token_encode)
   return {"status":1,"message":token}

@app.post("/auth/login-google")
async def auth_login_google(request:Request):
   object,[type,google_token]=await function_param_read("body",request,["type","google_token"],[])
   token=await function_login_google(type,google_token,request.app.state.client_postgres,config_key_jwt,config_token_expire_sec,google_user_read,config_google_login_client_id,function_token_encode)
   return {"status":1,"message":token}

@app.get("/my/profile")
async def my_profile(request:Request):
   user=await function_read_user_single(request.state.user["id"],request.app.state.client_postgres)
   asyncio.create_task(function_update_last_active_at_user(request.state.user["id"],request.app.state.client_postgres))
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   user=await function_read_user_single(request.state.user["id"],request.app.state.client_postgres)
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def my_account_delete(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   user=await function_read_user_single(request.state.user["id"],request.app.state.client_postgres)
   if user["api_access"]:return function_return_error("not allowed as you have api_access")
   await function_delete_user_single(mode,request.state.user["id"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def my_object_create(request:Request):
   object_1,[table,is_serialize,queue]=await function_param_read("query",request,["table"],["is_serialize","queue"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 1
   object["created_by_id"]=request.state.user["id"]
   if table in ["users"]:return function_return_error("table not allowed")
   if len(object)<=1:return function_return_error ("object issue")
   if any(key in config_column_disabled_non_admin_list for key in object):return function_return_error(" object key not allowed")
   if not queue:output=await function_postgres_object_create(table,[object],is_serialize,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   elif queue:
      data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
      if queue=="redis":output=await function_publish_redis(data,request.app.state.client_redis,config_channel_name)
      elif queue=="rabbitmq":output=await function_publish_rabbitmq(data,request.app.state.client_rabbitmq_channel,config_channel_name)
      elif queue=="lavinmq":output=await function_publish_lavinmq(data,request.app.state.client_lavinmq_channel,config_channel_name)
      elif queue=="kafka":output=await function_publish_kafka(data,request.app.state.client_kafka_producer,config_channel_name)
      elif "mongodb" in queue:output=await function_mongodb_object_create(table,[object],queue.split('_')[1],request.app.state.client_mongodb)
   return {"status":1,"message":output}

@app.get("/my/object-read")
async def my_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   output=await function_postgres_object_read(table,object,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize,function_create_where_string)
   return {"status":1,"message":output}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   object,[table,parent_table,parent_column,order,limit,page]=await function_param_read("query",request,["table","parent_table","parent_column"],["order","limit","page"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   output=await function_parent_object_read(table,parent_column,parent_table,order,limit,(page-1)*limit,request.state.user["id"],request.app.state.client_postgres)
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request):
   object_1,[table,otp]=await function_param_read("query",request,["table"],["otp"])
   object,[]=await function_param_read("body",request,[],[])
   object["updated_by_id"]=request.state.user["id"]
   if "id" not in object:return function_return_error ("id missing")
   if len(object)<=2:return function_return_error ("object length issue")
   if any(key in config_column_disabled_non_admin_list for key in object):return function_return_error(" object key not allowed")
   if table=="users":
      if object["id"]!=request.state.user["id"]:return function_return_error ("wrong id")
      if any(key in object and len(object)!=3 for key in ["password","email","mobile"]):return function_return_error("object length should be 2")
      if any(key in object and not otp for key in ["email","mobile"]):return function_return_error("otp missing")
      if otp:
         email,mobile=object.get("email"),object.get("mobile")
         if email:await function_otp_verify("email",otp,email,request.app.state.client_postgres)
         elif mobile:await function_otp_verify("mobile",otp,mobile,request.app.state.client_postgres)
   if table=="users":output=await function_postgres_object_update("users",[object],1,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   else:output=await function_postgres_object_update_user(table,[object],1,request.state.user["id"],request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   return {"status":1,"message":output}

@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   if table in ["users"]:return function_return_error("table not allowed")
   if column in config_column_disabled_non_admin_list:return function_return_error("column not allowed")
   await function_update_ids(table,ids,column,value,request.state.user["id"],request.state.user["id"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   if table in ["users"]:return function_return_error("table not allowed")
   await function_delete_ids(table,ids,request.state.user["id"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def my_object_delete_any(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   if table in ["users"]:return function_return_error("table not allowed")
   await function_postgres_object_delete_any(table,object,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize,function_create_where_string)
   return {"status":1,"message":"done"}

@app.get("/my/message-received")
async def my_message_received(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_received_user(request.state.user["id"],order,limit,(page-1)*limit,is_unread,request.app.state.client_postgres)
   if object_list:asyncio.create_task(function_message_object_mark_read(object_list,request.app.state.client_postgres))
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_inbox_user(request.state.user["id"],order,limit,(page-1)*limit,is_unread,request.app.state.client_postgres)
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request):
   object,[user_id,order,limit,page]=await function_param_read("query",request,["user_id"],["order","limit","page"])
   user_id=int(user_id)
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_thread_user(request.state.user["id"],user_id,order,limit,(page-1)*limit,request.app.state.client_postgres)
   asyncio.create_task(function_message_thread_mark_read(request.state.user["id"],user_id,request.app.state.client_postgres))
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete-bulk")
async def my_message_delete_bulk(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   if mode=="all":await function_message_delete_all_user(request.state.user["id"],request.app.state.client_postgres)
   if mode=="created":await function_message_delete_created_user(request.state.user["id"],request.app.state.client_postgres)
   if mode=="received":await function_message_delete_received_user(request.state.user["id"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.delete("/my/message-delete-single")
async def my_message_delete_single(request:Request):
   object,[id]=await function_param_read("query",request,["id"],[])
   await function_message_delete_single_user(request.state.user["id"],int(id),request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns")
async def public_otp_send_mobile_sns(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_otp_generate("mobile",mobile,request.app.state.client_postgres)
   await function_sns_send_message(mobile,str(otp),request.app.state.client_sns)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns-template")
async def public_otp_send_mobile_sns_template(request:Request):
   object,[mobile,message,template_id,entity_id,sender_id]=await function_param_read("body",request,["mobile","message","template_id","entity_id","sender_id"],[])
   otp=await function_otp_generate("mobile",mobile,request.app.state.client_postgres)
   await function_sns_send_message_template(mobile,message,template_id,entity_id,sender_id,request.app.state.client_sns)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def public_otp_send_mobile_fast2sms(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_otp_generate("mobile",mobile,request.app.state.client_postgres)
   await function_fast2sms_send_otp(mobile,otp,config_fast2sms_key,config_fast2sms_url)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_otp_generate("email",email,request.app.state.client_postgres)
   await function_ses_send_email([email],"your otp code",str(otp),sender_email,request.app.state.client_ses)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def public_otp_send_email_resend(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_otp_generate("email",email,request.app.state.client_postgres)
   await function_resend_send_email([email],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>",sender_email,config_resend_key,config_resend_url)
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def public_otp_verify_email(request:Request):
   object,[otp,email]=await function_param_read("body",request,["otp","email"],[])
   await function_otp_verify("email",otp,email,request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def public_otp_verify_mobile(request:Request):
   object,[otp,mobile]=await function_param_read("body",request,["otp","mobile"],[])
   await function_otp_verify("mobile",otp,mobile,request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 0
   if table not in config_table_allowed_public_create_list:return function_return_error("table not allowed")
   output=await function_postgres_object_create(table,[object],is_serialize,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   return {"status":1,"message":output}

@app.get("/public/object-read")
async def public_object_read(request:Request):
   object,[table,creator_data]=await function_param_read("query",request,["table"],["creator_data"])
   if table not in config_table_allowed_public_read_list:return function_return_error("table not allowed")
   object_list=await function_postgres_object_read(table,object,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize,function_create_where_string)
   if object_list and creator_data:object_list=await function_add_creator_data(object_list,creator_data,request.app.state.client_postgres)
   return {"status":1,"message":object_list}

@app.get("/public/info")
async def public_info(request:Request):
   output={
   "api_list":[route.path for route in request.app.routes],
   "postgres_schema":request.app.state.cache_postgres_schema
   }
   return {"status":1,"message":output}

@app.get("/public/page/{filename}")
async def public_page(filename:str):
   file_path=os.path.join(".",f"{filename}.html")
   if ".." in filename or "/" in filename:return function_return_error("invalid filename")
   if not os.path.isfile(file_path):return function_return_error ("file not found")
   with open(file_path, "r", encoding="utf-8") as file:html_content=file.read()
   return responses.HTMLResponse(content=html_content)

@app.post("/private/file-upload-s3-direct")
async def private_file_upload_s3_direct(request:Request):
   object,[bucket,file_list,key]=await function_param_read("form",request,["bucket","file_list"],["key"])
   key_list=key.split("---") if key else None
   output=await function_s3_file_upload_direct(bucket,key_list,file_list,request.app.state.client_s3,config_s3_region_name)
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   object,[bucket,key]=await function_param_read("body",request,["bucket","key"],[])
   output=await function_s3_file_upload_presigned(bucket,key,1000,100,request.app.state.client_s3,config_s3_region_name)
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def admin_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 1
   if request.app.state.cache_postgres_schema.get(table).get("created_by_id"):object["created_by_id"]=request.state.user["id"]
   output=await function_postgres_object_create(table,[object],is_serialize,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   object_1,[table]=await function_param_read("query",request,["table"],[])
   object,[]=await function_param_read("body",request,[],[])
   if "id" not in object:return function_return_error ("id missing")
   if len(object)<=1:return function_return_error ("object length issue")
   if request.app.state.cache_postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   output=await function_postgres_object_update(table,[object],1,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   await function_update_ids(table,ids,column,value,request.state.user["id"],None,request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   await function_delete_ids(table,ids,None,request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
async def admin_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   output=await function_postgres_object_read(table,object,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize,function_create_where_string)
   return {"status":1,"message":output}

@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   object,[query]=await function_param_read("body",request,["query"],[])
   output=await function_query_runner(query,request.state.user["id"],request.app.state.client_postgres,config_super_user_id_list)
   return {"status":1,"message":output}

#server start
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_server_start_uvicorn(app))
   except KeyboardInterrupt:print("exit")