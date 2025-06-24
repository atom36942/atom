#function
from function import *

#config
import json
env=function_load_env(".env")
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
config_gsheet_service_account_json_path=env.get("config_gsheet_service_account_json_path")
config_gsheet_scope_list=env.get("config_gsheet_scope_list").split(",") if env.get("config_gsheet_scope_list") else []
config_fast2sms_key=env.get("config_fast2sms_key")
config_fast2sms_url=env.get("config_fast2sms_url")
config_resend_key=env.get("config_resend_key")
config_resend_url=env.get("config_resend_url")
config_openai_key=env.get("config_openai_key")
config_token_expire_sec=int(env.get("config_token_expire_sec",365*24*60*60))
config_is_signup=int(env.get("config_is_signup",1))
config_limit_log_api_batch=int(env.get("config_limit_log_api_batch",10))
config_limit_cache_users_api_access=int(env.get("config_limit_cache_users_api_access",1000))
config_limit_cache_users_is_active=int(env.get("config_limit_cache_users_is_active",1000))
config_channel_name=env.get("config_channel_name","ch1")
config_column_disabled_non_admin_list=env.get("config_column_disabled_non_admin_list","is_active,is_verified,api_access").split(",")
config_table_allowed_public_create_list=env.get("config_table_allowed_public_create_list","test").split(",")
config_table_allowed_public_read_list=env.get("config_table_allowed_public_read_list","test").split(",")
router_list=env.get("router_list").split(",") if env.get("router_list") else []
config_api={
"/admin/object-create":{"id":1}, 
"/admin/object-update":{"id":2}, 
"/admin/ids-update":{"id":3}, 
"/admin/ids-delete":{"id":4}, 
"/admin/object-read":{"id":5}, 
"/admin/db-runner":{"id":6},
"/public/info":{"id":100,"rate_limiter":[3,10],"cache_sec":100},
"/my/object-read":{"is_active_check":1}, 
}
config_postgres={
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
"remark-text-0-gin,btree",
"location-geography(POINT)-0-gist",
"metadata-jsonb-0-gin"
],
"atom":[
"type-bigint-0-btree",
"title-text-0-0",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0"
],
"log_api":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"ip_address-text-0-0",
"api-text-0-0",
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
"drop_all_index":"0 DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'index_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;",
"default_created_at":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='created_at' AND table_schema='public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"default_updated_at_1":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';",
"default_updated_at_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected=1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"log_password_1":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;",
"log_password_2":"CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"root_user_1":"insert into users (type,username,password,api_access) values (1,'atom','5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5','1,2,3,4,5,6,7,8,9,10') on conflict do nothing;",
"root_user_2":"create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"delete_disable_bulk_function":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;",
"delete_disable_bulk_users":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"check_username":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"check_is_active":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_active' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_active', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_active IN (0,1) OR is_active IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
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
@asynccontextmanager
async def lifespan(app:FastAPI):
   try:
      #client init
      client_postgres=await function_postgres_client_read(config_postgres_url)
      client_postgres_asyncpg=await postgres_client_asyncpg_read(config_postgres_url)
      client_postgres_read=await function_postgres_client_read(config_postgres_url_read) if config_postgres_url_read else None
      client_redis=await function_redis_client_read(config_redis_url) if config_redis_url else None
      client_mongodb=await mongodb_client_read(config_mongodb_url) if config_mongodb_url else None
      client_s3,client_s3_resource=(await s3_client_read(config_s3_region_name,config_aws_access_key_id,config_aws_secret_access_key)) if config_s3_region_name else (None, None)
      client_sns=await sns_client_read(config_sns_region_name,config_aws_access_key_id,config_aws_secret_access_key) if config_sns_region_name else None
      client_ses=await ses_client_read(config_ses_region_name,config_aws_access_key_id,config_aws_secret_access_key) if config_ses_region_name else None
      client_openai=openai_client_read(config_openai_key) if config_openai_key else None
      client_gsheet=await gsheet_client_read(config_gsheet_service_account_json_path,config_gsheet_scope_list) if config_gsheet_service_account_json_path else None
      client_kafka_producer=await kafka_producer_client_read(config_kafka_url,config_kafka_path_cafile,config_kafka_path_certfile,config_kafka_path_keyfile,config_channel_name) if config_kafka_url else None
      client_rabbitmq,client_rabbitmq_channel=await function_rabbitmq_client_read(config_rabbitmq_url) if config_rabbitmq_url else None
      client_lavinmq,client_lavinmq_channel=await function_lavinmq_client_read(config_lavinmq_url) if config_lavinmq_url else None
      #cache init
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      if cache_postgres_schema.get("users",{}).get("api_access"):cache_users_api_access=await users_api_access_read(client_postgres_asyncpg,config_limit_cache_users_api_access)
      if cache_postgres_schema.get("users",{}).get("is_active"):cache_users_is_active=await users_is_active_read(client_postgres_asyncpg,config_limit_cache_users_is_active)
      #app state set
      for var_name,var_value in locals().items():
         if var_name.startswith(("client_", "cache_")):setattr(app.state,var_name,var_value)
      #app shutdown
      yield
      await client_postgres.disconnect()
      await client_postgres_asyncpg.close()
      if client_postgres_read:await client_postgres_read.close()
      if client_redis:await client_redis.aclose()
      if client_mongodb:await client_mongodb.close()
      if client_kafka_producer:await client_kafka_producer.stop()
      if client_rabbitmq_channel and not client_rabbitmq_channel.is_closed:await client_rabbitmq_channel.close()
      if client_rabbitmq and not client_rabbitmq.is_closed:await client_rabbitmq.close()
      if client_lavinmq_channel and not client_lavinmq_channel.is_closed:await client_lavinmq_channel.close()
      if client_lavinmq and not client_lavinmq.is_closed:await client_lavinmq.close()
   except Exception as e:print(str(e))
   
#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)
function_app_add_cors(app)
function_app_add_router(app,router_list)
if config_sentry_dsn:function_app_add_sentry(config_sentry_dsn)
if False:function_app_add_prometheus(app)

#middleware
from fastapi import Request
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
   try:
      start=time.time()
      response=None
      error=None
      api=request.url.path
      request.state.user=await function_token_check(request,config_key_root,config_key_jwt,function_token_decode)
      if "admin/" in request.url.path:await function_api_access_check(request,config_api,request.app.state.cache_users_api_access,request.app.state.client_postgres)
      if config_api.get(request.url.path,{}).get("is_active_check")==1 and request.state.user:await function_is_active_check(request,request.app.state.cache_users_is_active,request.app.state.client_postgres)
      if config_api.get(request.url.path,{}).get("rate_limiter"):await function_rate_limiter_check(request,config_api,request.app.state.client_redis)
      if request.query_params.get("is_background")=="1":response=await function_api_response_background(request,api_function)
      elif config_api.get(api,{}).get("cache_sec"):response=await function_api_response_cache("get",request,None,request.app.state.client_redis,None)
      if not response:
         response=await api_function(request)
         if config_api.get(api,{}).get("cache_sec"):response=await function_api_response_cache("set",request,response,request.app.state.client_redis,config_api.get(api,{}).get("cache_sec"))
   except Exception as e:
      error=str(e)
      print(traceback.format_exc())
      response=function_error(error)
      if config_sentry_dsn:sentry_sdk.capture_exception(e)
   object={"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"description":error}
   asyncio.create_task(log_api_create(object,config_limit_log_api_batch,function_postgres_create,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize))
   return response

#api
from fastapi import Request,responses
import json,time,os,asyncio,sys

@app.get("/")
async def index():
   return {"status":1,"message":"welcome to atom"}

@app.get("/root/postgres-init")
async def root_postgres_init(request:Request):
   await function_postgres_schema_init(request.app.state.client_postgres,function_postgres_schema_read,config_postgres)
   return {"status":1,"message":"done"}

@app.post("/root/postgres-uploader")
async def root_postgres_uploader(request:Request):
   object,[mode,table,file_list]=await function_param_read("form",request,["mode","table","file_list"],[])
   object_list=await function_file_to_object_list(file_list[-1])
   if mode=="create":output=await function_postgres_create(table,object_list,1,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   if mode=="update":output=await function_postgres_update(table,object_list,1,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   if mode=="delete":output=await function_postgres_delete(table,object_list,1,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.post("/root/redis-uploader")
async def root_redis_uploader(request:Request):
   object,[table,file_list,expiry]=await function_param_read("form",request,["table","file_list"],["expiry"])
   object_list=await function_file_to_object_list(file_list[-1])
   await function_redis_object_create(request.app.state.client_redis,table,object_list,expiry)
   return {"status":1,"message":"done"}

@app.post("/root/s3-bucket-ops")
async def root_s3_bucket_ops(request:Request):
   object,[mode,bucket]=await function_param_read("body",request,["mode","bucket"],[])
   if mode=="create":output=await function_s3_bucket_create(request.app.state.client_s3,bucket,config_s3_region_name)
   if mode=="public":output=await function_s3_bucket_public(request.app.state.client_s3,bucket)
   if mode=="empty":output=await function_s3_bucket_empty(request.app.state.client_s3_resource,bucket)
   if mode=="delete":output=await function_s3_bucket_delete(request.app.state.client_s3,bucket)
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   object,[url]=await function_param_read("body",request,["url"],[])
   for item in url.split("---"):output=await function_s3_url_delete(item,request.app.state.client_s3_resource)
   return {"status":1,"message":output}

@app.get("/root/reset-global")
async def root_reset_global(request:Request):
   request.app.state.cache_postgres_schema,request.app.state.cache_postgres_column_datatype=await function_postgres_schema_read(request.app.state.client_postgres)
   request.app.state.cache_users_api_access=await users_api_access_read(request.app.state.client_postgres_asyncpg,config_limit_cache_users_api_access)
   request.app.state.cache_users_is_active=await users_is_active_read(request.app.state.client_postgres_asyncpg,config_limit_cache_users_is_active) 
   return {"status":1,"message":"done"}
   
@app.post("/auth/signup")
async def auth_signup(request:Request):
   if config_is_signup==0:return function_error("signup disabled")
   object,[type,username,password]=await function_param_read("body",request,["type","username","password"],[])
   user=await function_signup_username_password(request.app.state.client_postgres,type,username,password)
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return {"status":1,"message":token}

@app.post("/auth/signup-bigint")
async def auth_signup_bigint(request:Request):
   if config_is_signup==0:return function_error("signup disabled")
   object,[type,username,password]=await function_param_read("body",request,["type","username","password"],[])
   user=await function_signup_username_password_bigint(request.app.state.client_postgres,type,username,password)
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return {"status":1,"message":token}

@app.post("/auth/login-password-username")
async def auth_login_password_username(request:Request):
   object,[type,password,username]=await function_param_read("body",request,["type","password","username"],[])
   token=await function_login_password_username(request.app.state.client_postgres,function_token_create,config_key_jwt,config_token_expire_sec,type,password,username)
   return {"status":1,"message":token}

@app.post("/auth/login-password-bigint")
async def auth_login_password_bigint(request:Request):
   object,[type,password,username]=await function_param_read("body",request,["type","password","username"],[])
   token=await function_login_password_username_bigint(request.app.state.client_postgres,function_token_create,config_key_jwt,config_token_expire_sec,type,password,username)
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   object,[type,password,email]=await function_param_read("body",request,["type","password","email"],[])
   token=await function_login_password_email(request.app.state.client_postgres,function_token_create,config_key_jwt,config_token_expire_sec,type,password,email)
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   object,[type,password,mobile]=await function_param_read("body",request,["type","password","mobile"],[])
   token=await function_login_password_mobile(request.app.state.client_postgres,function_token_create,config_key_jwt,config_token_expire_sec,type,password,mobile)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def auth_login_otp_email(request:Request):
   object,[type,otp,email]=await function_param_read("body",request,["type","otp","email"],[])
   token=await function_login_otp_email(request.app.state.client_postgres,function_token_create,config_key_jwt,config_token_expire_sec,function_verify_otp,type,otp,email)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-mobile")
async def auth_login_otp_mobile(request:Request):
   object,[type,otp,mobile]=await function_param_read("body",request,["type","otp","mobile"],[])
   token=await function_login_otp_mobile(request.app.state.client_postgres,function_token_create,config_key_jwt,config_token_expire_sec,function_verify_otp,type,otp,mobile)
   return {"status":1,"message":token}

@app.post("/auth/login-google")
async def auth_login_google(request:Request):
   object,[type,google_token]=await function_param_read("body",request,["type","google_token"],[])
   token=await function_login_google(request.app.state.client_postgres,function_token_create,config_key_jwt,config_token_expire_sec,google_user_read,config_google_login_client_id,type,google_token)
   return {"status":1,"message":token}

@app.get("/my/profile")
async def my_profile(request:Request):
   user=await read_user_single(request.app.state.client_postgres,request.state.user["id"])
   asyncio.create_task(function_update_user_last_active_at(request.app.state.client_postgres,request.state.user["id"]))
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   user=await read_user_single(request.app.state.client_postgres,request.state.user["id"])
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def my_account_delete(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   user=await read_user_single(request.app.state.client_postgres,request.state.user["id"])
   if user["api_access"]:return function_error("not allowed as you have api_access")
   await function_delete_user(mode,request.app.state.client_postgres,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def my_object_create(request:Request):
   object_1,[table,is_serialize,queue]=await function_param_read("query",request,["table"],["is_serialize","queue"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 1
   object["created_by_id"]=request.state.user["id"]
   if table in ["users"]:return function_error("table not allowed")
   if len(object)<=1:return function_error ("object issue")
   if any(key in config_column_disabled_non_admin_list for key in object):return function_error(" object key not allowed")
   if not queue:output=await function_postgres_create(table,[object],is_serialize,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   elif queue:
      data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
      if queue=="redis":output=await function_redis_publish(request.app.state.client_redis,config_channel_name,data)
      elif queue=="rabbitmq":output=await function_rabbitmq_publish(request.app.state.client_rabbitmq_channel,config_channel_name,data)
      elif queue=="lavinmq":output=await function_lavinmq_publish(request.app.state.client_lavinmq_channel,config_channel_name,data)
      elif queue=="kafka":output=await function_kafka_publish(request.app.state.client_kafka_producer,config_channel_name,data)
      elif "mongodb" in queue:output=await mongodb_create_object(request.app.state.client_mongodb,queue.split('_')[1],table,[object])
   return {"status":1,"message":output}

@app.get("/my/object-read")
async def my_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   output=await function_postgres_read(table,object,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize,create_where_string)
   return {"status":1,"message":output}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   object,[table,parent_table,parent_column,order,limit,page]=await function_param_read("query",request,["table","parent_table","parent_column"],["order","limit","page"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   output=await function_postgres_parent_read(table,parent_column,parent_table,request.app.state.client_postgres,order,limit,(page-1)*limit,request.state.user["id"])
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request):
   object_1,[table,otp]=await function_param_read("query",request,["table"],["otp"])
   object,[]=await function_param_read("body",request,[],[])
   object["updated_by_id"]=request.state.user["id"]
   if "id" not in object:return function_error ("id missing")
   if len(object)<=2:return function_error ("object length issue")
   if any(key in config_column_disabled_non_admin_list for key in object):return function_error(" object key not allowed")
   if table=="users":
      if object["id"]!=request.state.user["id"]:return function_error ("wrong id")
      if any(key in object and len(object)!=3 for key in ["password","email","mobile"]):return function_error("object length should be 2")
      if any(key in object and not otp for key in ["email","mobile"]):return function_error("otp missing")
      if otp:
         email,mobile=object.get("email"),object.get("mobile")
         await function_verify_otp(request.app.state.client_postgres,otp,email,mobile)
   if table=="users":output=await function_postgres_update("users",[object],1,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   else:output=await function_postgres_update_user(table,[object],1,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize,request.state.user["id"])
   return {"status":1,"message":output}

@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   if table in ["users"]:return function_error("table not allowed")
   if column in config_column_disabled_non_admin_list:return function_error("column not allowed")
   await function_postgres_update_ids(request.app.state.client_postgres,table,ids,column,value,request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   if table in ["users"]:return function_error("table not allowed")
   await function_postgres_delete_ids(request.app.state.client_postgres,table,ids,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def my_object_delete_any(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   if table in ["users"]:return function_error("table not allowed")
   await function_postgres_delete_any(table,object,request.app.state.client_postgres,create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":"done"}

@app.get("/my/message-received")
async def my_message_received(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_received_user(request.app.state.client_postgres,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   if object_list:asyncio.create_task(function_mark_message_object_read(request.app.state.client_postgres,object_list))
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_inbox_user(request.app.state.client_postgres,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request):
   object,[user_id,order,limit,page]=await function_param_read("query",request,["user_id"],["order","limit","page"])
   user_id=int(user_id)
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_thread_user(request.app.state.client_postgres,request.state.user["id"],user_id,order,limit,(page-1)*limit)
   asyncio.create_task(function_mark_message_read_thread(request.app.state.client_postgres,request.state.user["id"],user_id))
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete-bulk")
async def my_message_delete_bulk(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   if mode=="all":await function_message_delete_user_all(request.app.state.client_postgres,request.state.user["id"])
   if mode=="created":await function_message_delete_user_created(request.app.state.client_postgres,request.state.user["id"])
   if mode=="received":await function_message_delete_user_received(request.app.state.client_postgres,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/message-delete-single")
async def my_message_delete_single(request:Request):
   object,[id]=await function_param_read("query",request,["id"],[])
   await function_message_delete_user_single(request.app.state.client_postgres,request.state.user["id"],int(id))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns")
async def public_otp_send_mobile_sns(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_generate_save_otp(request.app.state.client_postgres,None,mobile)
   await function_sns_send_message(request.app.state.client_sns,mobile,str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns-template")
async def public_otp_send_mobile_sns_template(request:Request):
   object,[mobile,template_id,entity_id,sender_id,message]=await function_param_read("body",request,["mobile","template_id","entity_id","sender_id","message"],[])
   otp=await function_generate_save_otp(request.app.state.client_postgres,None,mobile)
   await function_sns_send_message_template(request.app.state.client_sns,mobile,template_id,entity_id,sender_id,message)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def public_otp_send_mobile_fast2sms(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_generate_save_otp(request.app.state.client_postgres,None,mobile)
   await function_otp_send_mobile_fast2sms(config_fast2sms_url,config_fast2sms_key,mobile,otp)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_generate_save_otp(request.app.state.client_postgres,email,None)
   await function_send_email_ses(request.app.state.client_ses,sender_email,[email],"your otp code",str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def public_otp_send_email_resend(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_generate_save_otp(request.app.state.client_postgres,email,None)
   await function_send_email_resend(config_resend_key,config_resend_url,sender_email,[email],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def public_otp_verify_email(request:Request):
   object,[otp,email]=await function_param_read("body",request,["otp","email"],[])
   await function_verify_otp(request.app.state.client_postgres,otp,email,None)
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def public_otp_verify_mobile(request:Request):
   object,[otp,mobile]=await function_param_read("body",request,["otp","mobile"],[])
   await function_verify_otp(request.app.state.client_postgres,otp,None,mobile)
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 0
   if table not in config_table_allowed_public_create_list:return function_error("table not allowed")
   output=await function_postgres_create(table,[object],is_serialize,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.get("/public/object-read")
async def public_object_read(request:Request):
   object,[table,creator_data]=await function_param_read("query",request,["table"],["creator_data"])
   if table not in config_table_allowed_public_read_list:return function_error("table not allowed")
   object_list=await function_postgres_read(table,object,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize,create_where_string)
   if object_list and creator_data:object_list=await function_add_creator_data(request.app.state.client_postgres,object_list,creator_data)
   return {"status":1,"message":object_list}

public_info_cache={}
@app.get("/public/info")
async def public_info(request:Request):
   global public_info_cache
   if not public_info_cache or (time.time()-public_info_cache.get("set_at")>=1000):
      public_info_cache={
      "set_at":time.time(),
      "api_list":[route.path for route in request.app.routes],
      "redis":await request.app.state.client_redis.info() if request.app.state.client_redis else None,
      "bucket":request.app.state.client_s3.list_buckets() if request.app.state.client_s3 else None,
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True))
      }
   return {"status":1,"message":public_info_cache}

@app.get("/public/page/{filename}")
async def public_page(filename:str):
   file_path=os.path.join(".",f"{filename}.html")
   if ".." in filename or "/" in filename:return function_error("invalid filename")
   if not os.path.isfile(file_path):return function_error ("file not found")
   with open(file_path, "r", encoding="utf-8") as file:html_content=file.read()
   return responses.HTMLResponse(content=html_content)

@app.post("/private/file-upload-s3-direct")
async def private_file_upload_s3_direct(request:Request):
   object,[bucket,file_list,key]=await function_param_read("form",request,["bucket","file_list"],["key"])
   key_list=key.split("---") if key else None
   output=await function_s3_file_upload_direct(request.app.state.client_s3,config_s3_region_name,bucket,key_list,file_list)
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   object,[bucket,key]=await function_param_read("body",request,["bucket","key"],[])
   output=await s3_file_upload_presigned(request.app.state.client_s3,config_s3_region_name,bucket,key,1000,100)
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def admin_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 1
   if request.app.state.cache_postgres_schema.get(table).get("created_by_id"):object["created_by_id"]=request.state.user["id"]
   output=await function_postgres_create(table,[object],is_serialize,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   object_1,[table]=await function_param_read("query",request,["table"],[])
   object,[]=await function_param_read("body",request,[],[])
   if "id" not in object:return function_error ("id missing")
   if len(object)<=1:return function_error ("object length issue")
   if request.app.state.cache_postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   output=await function_postgres_update(table,[object],1,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   await function_postgres_update_ids(request.app.state.client_postgres,table,ids,column,value,request.state.user["id"],None)
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   await function_postgres_delete_ids(request.app.state.client_postgres,table,ids,None)
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
async def admin_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   output=await function_postgres_read(table,object,request.app.state.client_postgres,request.app.state.cache_postgres_column_datatype,function_object_serialize,create_where_string)
   return {"status":1,"message":output}

@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   object,[query]=await function_param_read("body",request,["query"],[])
   output=await postgres_query_runner(request.app.state.client_postgres,query,request.state.user["id"])
   return {"status":1,"message":output}

#server start
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_uvicorn_server_start(app))
   except KeyboardInterrupt:print("exit")