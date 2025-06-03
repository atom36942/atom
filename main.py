#import file
from function import *
if os.path.exists("config.py"):import config

#env
import os
from dotenv import load_dotenv
load_dotenv()
postgres_url=os.getenv("postgres_url")
redis_url=os.getenv("redis_url")
key_jwt=os.getenv("key_jwt")
key_root=os.getenv("key_root")
valkey_url=os.getenv("valkey_url")
sentry_dsn=os.getenv("sentry_dsn")
mongodb_url=os.getenv("mongodb_url")
rabbitmq_url=os.getenv("rabbitmq_url")
lavinmq_url=os.getenv("lavinmq_url")
kafka_url=os.getenv("kafka_url")
kafka_path_cafile=os.getenv("kafka_path_cafile")
kafka_path_certfile=os.getenv("kafka_path_certfile")
kafka_path_keyfile=os.getenv("kafka_path_keyfile")
aws_access_key_id=os.getenv("aws_access_key_id")
aws_secret_access_key=os.getenv("aws_secret_access_key")
s3_region_name=os.getenv("s3_region_name")
sns_region_name=os.getenv("sns_region_name")
ses_region_name=os.getenv("ses_region_name")
google_client_id=os.getenv("google_client_id")
is_signup=int(os.getenv("is_signup",1))
postgres_url_read=os.getenv("postgres_url_read")
channel_name=os.getenv("channel_name","ch1")
user_type_allowed=[int(x) for x in (os.getenv("user_type_allowed","1,2,3").split(","))]
column_disabled_non_admin=os.getenv("column_disabled_non_admin","is_active,is_verified,api_access").split(",")
postgres_url_read_replica=os.getenv("postgres_url_read_replica")
router_list=os.getenv("router_list").split(",") if os.getenv("router_list") else []
fast2sms_key=os.getenv("fast2sms_key")
cache_client=os.getenv("cache_client")
ratelimiter_client=os.getenv("ratelimiter_client")
is_active_check_api_keyword=os.getenv("is_active_check_api_keyword")
table_allowed_public_create=os.getenv("table_allowed_public_create","test")
table_allowed_public_read=os.getenv("table_allowed_public_read","test")
table_allowed_private_read=os.getenv("table_allowed_private_read","test")
log_api_batch_count=int(os.getenv("log_api_batch_count",10))
users_api_access_max_count=int(os.getenv("users_api_access_max_count",100000))
users_is_active_max_count=int(os.getenv("users_is_active_max_count",1000))
openai_key=os.getenv("openai_key")
token_expire_sec=int(os.getenv("token_expire_sec",365*24*60*60))
gsheet_service_account_json_path=os.getenv("gsheet_service_account_json_path")
gsheet_scope_list=os.getenv("gsheet_scope_list","https://www.googleapis.com/auth/spreadsheets").split(",")
resend_key=os.getenv("resend_key")

#globals runtime
postgres_client=None
postgres_client_asyncpg=None
postgres_client_read_replica=None
postgres_schema={}
postgres_column_datatype={}
users_api_access={}
users_is_active={}
redis_client=None
valkey_client=None
mongodb_client=None
s3_client=None
s3_resource=None
sns_client=None
ses_client=None
rabbitmq_client=None
rabbitmq_channel=None
lavinmq_client=None
lavinmq_channel=None
kafka_producer_client=None
gsheet_client=None
openai_client=None

#globals fixed
postgres_config_default={
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
"metadata-jsonb-0-0"
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
"api-text-0-0",
"method-text-0-0",
"query_param-text-0-0",
"status_code-smallint-0-0",
"response_time_ms-numeric(1000,3)-0-0"
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
"root_user_1":"insert into users (type,username,password,api_access) values (1,'atom','5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5','/admin/object-create,/admin/object-update,/admin/object-read,/admin/ids-update,/admin/ids-delete,/admin/db-runner') on conflict do nothing;",
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

#openai client
from openai import OpenAI
if openai_key:openai_client=OpenAI(api_key=openai_key)

# sentry
import sentry_sdk
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)

#redis key builder
from fastapi import Request,Response
import jwt,json,hashlib
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param_sorted=str(dict(sorted(request.query_params.items())))
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   user_id=0
   if "my/" in api:user_id=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])["id"]
   key=f"{api}---{query_param_sorted}---{str(user_id)}".lower()
   if False:key=hashlib.sha256(str(key).encode()).hexdigest()
   return key

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_limiter import FastAPILimiter
@asynccontextmanager
async def lifespan(app:FastAPI):
   try:
      #postgres client
      global postgres_client
      postgres_client=await postgres_client_read(postgres_url)
      #postgres client asyncpg
      global postgres_client_asyncpg
      postgres_client_asyncpg=await postgres_client_asyncpg_read(postgres_url)
      #postgres client read replica
      global postgres_client_read_replica
      if postgres_url_read_replica:postgres_client_read_replica=await postgres_client_read(postgres_url_read_replica)
      #postgres schema
      global postgres_schema
      postgres_schema=await postgres_schema_read(postgres_client)
      #postgres column datatype
      global postgres_column_datatype
      postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
      #redis client
      global redis_client
      if redis_url:redis_client=await redis_client_read(redis_url)
      #valkey client
      global valkey_client
      if valkey_url:valkey_client=await redis_client_read(valkey_url)
      #users api access
      global users_api_access
      if postgres_schema.get("users"):users_api_access=await users_api_access_read(postgres_client_asyncpg,users_api_access_max_count)
      #users is_active
      global users_is_active
      if postgres_schema.get("users"):users_is_active=await users_is_active_read(postgres_client_asyncpg,users_is_active_max_count)
      #mongodb client
      global mongodb_client
      if mongodb_url:mongodb_client=await mongodb_client_read(mongodb_url)
      #s3 client
      global s3_client,s3_resource
      if s3_region_name:s3_client,s3_resource=await s3_client_read(s3_region_name,aws_access_key_id,aws_secret_access_key)
      #sns client
      global sns_client
      if sns_region_name:sns_client=await sns_client_read(sns_region_name,aws_access_key_id,aws_secret_access_key)
      #ses client
      global ses_client
      if ses_region_name:ses_client=await ses_client_read(ses_region_name,aws_access_key_id,aws_secret_access_key)
      #rabbitmq client
      global rabbitmq_client,rabbitmq_channel
      if rabbitmq_url:rabbitmq_client,rabbitmq_channel=await rabbitmq_client_read(rabbitmq_url,channel_name)
      #lavinmq client
      global lavinmq_client,lavinmq_channel
      if lavinmq_url:lavinmq_client,lavinmq_channel=await lavinmq_client_read(lavinmq_url,channel_name)
      #kafka producer client
      global kafka_producer_client
      if kafka_url:kafka_producer_client=await kafka_producer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name)
      #cache
      if valkey_client and cache_client=="valkey":await cache_init(valkey_client,redis_key_builder)
      else:await cache_init(redis_client,redis_key_builder)
      #ratelimiter
      if valkey_client and ratelimiter_client=="valkey":await FastAPILimiter.init(valkey_client)
      else:await FastAPILimiter.init(redis_client)
      #gsheet client
      global gsheet_client
      if gsheet_service_account_json_path:gsheet_client=await gsheet_client_read(gsheet_service_account_json_path,gsheet_scope_list)
      #disconnect
      yield
      await postgres_client.disconnect()
      await postgres_client_asyncpg.close()
      if postgres_client_read_replica:await postgres_client_read_replica.close()
      if redis_client:await redis_client.aclose()
      if valkey_client:await valkey_client.aclose()
      if rabbitmq_client and rabbitmq_channel.is_open:rabbitmq_channel.close()
      if rabbitmq_client and rabbitmq_client.is_open:rabbitmq_client.close()
      if lavinmq_client and lavinmq_channel.is_open:lavinmq_channel.close()
      if lavinmq_client and lavinmq_client.is_open:lavinmq_client.close()
      if kafka_producer_client:await kafka_producer_client.stop()
      await FastAPILimiter.close()
   except Exception as e:print(str(e))
   
#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#prometheus
from prometheus_fastapi_instrumentator import Instrumentator
if False:Instrumentator().instrument(app).expose(app)

#middleware
from fastapi import Request
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request:Request,api_function):
   try:
      start=time.time()
      token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
      #router shared state
      if router_list:
         request.state.postgres_client=postgres_client
         request.state.postgres_column_datatype=postgres_column_datatype
      #token check
      for item in ["root/","my/","private/","admin/"]:
         if item in request.url.path and not token:return error("token missing")
      #token decode
      request.state.user={}
      if token:
         if "root/" in request.url.path:
            if token!=key_root:return error("token root mismatch")
         else:request.state.user=await token_decode(token,key_jwt)
      #admin check
      if "admin/" in request.url.path:await users_api_access_check(request,users_api_access,postgres_client)
      #is_active check
      if is_active_check_api_keyword:
         for item in is_active_check_api_keyword.split(","):
            if item in request.url.path:await users_is_active_check(request.state.user["id"],users_is_active,postgres_client)
      #api response
      if request.query_params.get("is_background")=="1":response=await api_response_background(request,api_function)
      else:response=await api_function(request)
      #api log
      object={"created_by_id":request.state.user.get("id",None),"api":request.url.path,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000}
      asyncio.create_task(log_api_create(object,log_api_batch_count,postgres_create,postgres_client,postgres_column_datatype,object_serialize))
   except Exception as e:
      print(traceback.format_exc())
      response=error(str(e))
      if sentry_dsn:sentry_sdk.capture_exception(e)
   #final
   return response

#router
router_add(router_list,app)

#api
from fastapi import Request,responses,Depends
import hashlib,json,time,os,random,asyncio,requests,httpx
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter

@app.get("/")
async def index():
   return {"status":1,"message":"welcome to atom"}

@app.post("/root/db-init")
async def root_db_init(request:Request):
   #param
   mode=request.query_params.get("mode")
   if not mode:return error("mode missing")
   #variable
   if mode=="1":postgres_config=postgres_config_default
   elif mode=="2":postgres_config=config.postgres_config_client
   elif mode=="3":postgres_config=await request.json()
   #logic
   await postgres_schema_init(postgres_client,postgres_schema_read,postgres_config)
   #postgres schema reset
   global postgres_schema
   postgres_schema=await postgres_schema_read(postgres_client)
   #postgres column datatype reset
   global postgres_column_datatype
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   #final
   return {"status":1,"message":"done"}

@app.post("/root/db-uploader")
async def root_db_uploader(request:Request):
   #param
   object,file_list=await form_data_read(request)
   mode=object.get("mode")
   table=object.get("table")
   is_serialize=int(object.get("is_serialize",1))
   if not mode or not table or not file_list:return error("mode/table/file missing")
   #object list
   object_list=await file_to_object_list(file_list[-1])
   #logic
   if mode=="create":output=await postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="update":output=await postgres_update(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="delete":output=await postgres_delete(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   #final
   return {"status":1,"message":output}

@app.post("/root/redis-uploader")
async def root_redis_uploader(request:Request):
   #param
   object,file_list=await form_data_read(request)
   table=object.get("table")
   expiry=object.get("expiry")
   if not table or not file_list:return error("table/file missing")
   #object list
   object_list=await file_to_object_list(file_list[-1])
   #logic
   await redis_object_create(redis_client,table,object_list,expiry)
   #final
   return {"status":1,"message":"done"}

@app.delete("/root/redis-reset")
async def root_reset_redis():
   #logic
   if redis_client:await redis_client.flushall()
   if valkey_client:await valkey_client.flushall()
   #final
   return {"status":1,"message":"done"}

@app.put("/root/reset-global")
async def root_reset_global():
   #postgres schema reset
   global postgres_schema
   postgres_schema=await postgres_schema_read(postgres_client)
   #postgres column datatype reset
   global postgres_column_datatype
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   #users api access reset
   global users_api_access
   if postgres_schema.get("users"):users_api_access=await users_api_access_read(postgres_client_asyncpg,users_api_access_max_count)
   #users is_active reset
   global users_is_active
   if postgres_schema.get("users"):users_is_active=await users_is_active_read(postgres_client_asyncpg,users_is_active_max_count)
   #final
   return {"status":1,"message":"done"}

@app.put("/root/db-checklist")
async def root_db_checklist():
   #root user always active
   query="update users set is_active=1,is_deleted=null where id=1;"
   await postgres_client.execute(query=query,values={})
   #delete log
   query="delete from log_api where created_at<now()-interval '30 days';"
   if postgres_schema.get("log_api"):await postgres_client.execute(query=query,values={})
   #delete otp
   query="delete from otp where created_at<now()-interval '30 days';"
   if postgres_schema.get("otp"):await postgres_client.execute(query=query,values={})
   #delete message
   query="delete from message where created_at<now()-interval '30 days';"
   if postgres_schema.get("message"):await postgres_client.execute(query=query,values={})
   #final
   return {"status":1,"message":"done"}

@app.post("/root/s3-bucket-ops")
async def root_s3_bucket_ops(request:Request):
   #param
   mode=request.query_params.get("mode")
   bucket=request.query_params.get("bucket")
   if not mode or not bucket:return error("mode/bucket missing")
   #logic
   if mode=="create":output=await s3_bucket_create(s3_client,bucket,s3_region_name)
   if mode=="public":output=await s3_bucket_public(s3_client,bucket)
   if mode=="empty":output=await s3_bucket_empty(s3_resource,bucket)
   if mode=="delete":output=await s3_bucket_delete(s3_client,bucket)
   #final
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   #param
   url=request.query_params.get("url")
   if not url:return error("url missing")
   #logic
   for item in url.split("---"):output=await s3_url_delete(item,s3_resource)
   #final
   return {"status":1,"message":output}

@app.post("/auth/signup-username-password",dependencies=[Depends(RateLimiter(times=1,seconds=5))])
async def auth_signup_username_password(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return error("type/username/password missing")
   #check
   if is_signup==0:return error("signup disabled")
   if type not in user_type_allowed:return error("wrong type")
   #logic
   user=await signup_username_password(postgres_client,type,username,password)
   token=await token_create(key_jwt,token_expire_sec,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/signup-username-password-bigint")
async def auth_signup_username_password_bigint(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username_bigint=object.get("username_bigint")
   password_bigint=object.get("password_bigint")
   if not type or not username_bigint or not password_bigint:return error("type/username_bigint/password_bigint missing")
   #check
   if is_signup==0:return error("signup disabled")
   if type not in user_type_allowed:return error("wrong type")
   #logic
   user=await signup_username_password_bigint(postgres_client,type,username_bigint,password_bigint)
   token=await token_create(key_jwt,token_expire_sec,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-username")
async def auth_login_password_username(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return error("type/username/password missing")
   #logic
   token=await login_password_username(postgres_client,token_create,key_jwt,token_expire_sec,type,username,password)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-username-bigint")
async def auth_login_password_username_bigint(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username_bigint=object.get("username_bigint")
   password_bigint=object.get("password_bigint")
   if not type or not username_bigint or not password_bigint:return error("type/username_bigint/password_bigint missing")
   #logic
   token=await login_password_username_bigint(postgres_client,token_create,key_jwt,token_expire_sec,type,username_bigint,password_bigint)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   email=object.get("email")
   password=object.get("password")
   if not type or not email or not password:return error("type/email/password missing")
   #logic
   token=await login_password_email(postgres_client,token_create,key_jwt,token_expire_sec,type,email,password)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   mobile=object.get("mobile")
   password=object.get("password")
   if not type or not mobile or not password:return error("type/mobile/password missing")
   #logic
   token=await login_password_mobile(postgres_client,token_create,key_jwt,token_expire_sec,type,mobile,password)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def auth_login_otp_email(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   email=object.get("email")
   otp=object.get("otp")
   if not type or not email or not otp:return error("type/email/otp missing")
   #check
   if type not in user_type_allowed:return error("wrong type")
   #logic
   token=await login_otp_email(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,email,otp)
   #final
   return {"status":1,"message":token}
   
@app.post("/auth/login-otp-mobile")
async def auth_login_otp_mobile(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   mobile=object.get("mobile")
   otp=object.get("otp")
   if not type or not mobile or not otp:return error("type/mobile/otp missing")
   #check
   if type not in user_type_allowed:return error("wrong type")
   #logic
   token=await login_otp_mobile(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,mobile,otp)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-oauth-google")
async def auth_login_oauth_google(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   google_token=object.get("google_token")
   if not type or not google_token:return error("type/google_token missing")
   #check
   if type not in user_type_allowed:return error("wrong type")
   #logic
   token=await login_google(postgres_client,token_create,key_jwt,token_expire_sec,google_user_read,google_client_id,type,google_token)
   #final
   return {"status":1,"message":token}

@app.get("/my/profile")
async def my_profile(request:Request):
   #logic
   user=await read_user_single(postgres_client,request.state.user["id"])
   asyncio.create_task(update_user_last_active_at(postgres_client,request.state.user["id"]))
   #final
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   #read user
   user=await read_user_single(postgres_client,request.state.user["id"])
   #token create
   token=await token_create(key_jwt,token_expire_sec,user)
   #final
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def my_account_delete(request:Request):
   #param
   mode=request.query_params.get("mode")
   if not mode:return error("mode missing")
   #check user
   user=await read_user_single(postgres_client,request.state.user["id"])
   if user["api_access"]:return error("not allowed as you have api_access")
   #logic
   if mode=="soft":
      query="update users set is_deleted=1 where id=:id;"
      values={"id":request.state.user["id"]}
      await postgres_client.execute(query=query,values=values)
   elif mode=="hard":
      query="delete from users where id=:id;"
      values={"id":request.state.user["id"]}
      await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def my_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   queue=request.query_params.get("queue")
   object=await request.json()
   if not table:return error("table missing")
   #modify
   object["created_by_id"]=request.state.user["id"]
   #check
   if table in ["users"]:return error("table not allowed")
   if len(object)<=1:return error ("object issue")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   #logic
   data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
   if not queue:output=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   elif queue=="redis":output=await redis_client.publish(channel_name,json.dumps(data))
   elif queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
   elif queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
   elif queue=="kafka":output=await kafka_producer_client.send_and_wait(channel_name,json.dumps(data,indent=2).encode('utf-8'),partition=0)
   elif "mongodb" in queue:output=await mongodb_create_object(mongodb_client,queue.split('_')[1],table,[object])
   #final
   return {"status":1,"message":output}

@app.get("/my/object-read")
@cache(expire=60)
async def my_object_read(request:Request):
   #param
   object=dict(request.query_params)
   table=object.get("table")
   if not table:return error("table missing")
   #modify
   object["created_by_id"]=f"=,{request.state.user['id']}"
   #logic
   output=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   #final
   return {"status":1,"message":output}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   table=request.query_params.get("table")
   parent_column=request.query_params.get("parent_column")
   parent_table=request.query_params.get("parent_table")
   if not table or not parent_column:return error("table/parent_column/parent_table missing")
   #logic
   output=await postgres_parent_read(table,parent_column,parent_table,postgres_client,order,limit,(page-1)*limit,request.state.user["id"])
   #final
   return {"status":1,"message":output}

@app.put("/my/user-update")
async def my_user_update(request:Request):
   #param
   object=await request.json()
   otp=int(request.query_params.get("otp",0))
   #modify
   object["updated_by_id"]=request.state.user["id"]
   #check
   if "id" not in object:return error ("id missing")
   if object["id"]!=request.state.user["id"]:return error ("wrong id")
   if len(object)<=2:return error ("object length issue")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   if any(key in object and len(object)!=3 for key in ["password","email","mobile"]):return error("object length should be 2")
   if any(key in object and not otp for key in ["email","mobile"]):return error("otp missing")
   #otp verify
   if otp>0:
      email,mobile=object.get("email"),object.get("mobile")
      await verify_otp(postgres_client,otp,email,mobile)
   #logic
   output=await postgres_update("users",[object],1,postgres_client,postgres_column_datatype,object_serialize)
   #final
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if not table:return error("table missing")
   #modify
   object["updated_by_id"]=request.state.user["id"]
   #check
   if table in ["users"]:return error("table not allowed")
   if "id" not in object:return error ("id missing")
   if len(object)<=2:return error ("object length issue")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   #logic
   output=await postgres_update_user(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize,request.state.user["id"])
   #final
   return {"status":1,"message":output}

@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   del object["table"]
   del object["ids"]
   key,value=next(reversed(object.items()),(None, None))
   if not table or not ids or not key:return error("table/ids/key must")
   #check
   if table in ["users"]:return error("table not allowed")
   if key in column_disabled_non_admin:return error("column not allowed")
   #logic
   await postgres_update_ids(postgres_client,table,ids,key,value,request.state.user["id"],request.state.user["id"])
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   if not table or not ids:return error("table/ids must")
   #check
   if table in ["users"]:return error("table not allowed")
   #logic
   await postgres_delete_ids(postgres_client,table,ids,request.state.user["id"])
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def my_object_delete_any(request:Request):
   #param
   table=request.query_params.get("table")
   object=dict(request.query_params)
   if not table:return error("table missing")
   #modify
   object["created_by_id"]=f"=,{request.state.user['id']}"
   #check
   if table in ["users"]:return error("table not allowed")
   #logic
   await postgres_delete_any(table,object,postgres_client,create_where_string,object_serialize,postgres_column_datatype)
   #final
   return {"status":1,"message":"done"}

@app.get("/my/message-received")
async def my_message_received(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   is_unread=request.query_params.get("is_unread")
   #logic
   object_list=await message_received_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   #mark message read
   if object_list:
      ids=','.join([str(item['id']) for item in object_list])
      query=f"update message set is_read=1 where id in ({ids});"
      asyncio.create_task(postgres_client.execute(query=query,values={}))
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   is_unread=request.query_params.get("is_unread")
   #logic
   object_list=await message_inbox_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   user_id=int(request.query_params.get("user_id",0))
   if not user_id:return error("user_id missing")
   #logic
   object_list=await message_thread_user(postgres_client,request.state.user["id"],user_id,order,limit,(page-1)*limit)
   #mark message thread read
   asyncio.create_task(mark_message_read_thread(postgres_client,request.state.user["id"],user_id))
   #final
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete")
async def my_message_delete(request:Request):
   #param
   mode=request.query_params.get("mode")
   id=int(request.query_params.get("id",0))
   if not mode:return error("mode missing")
   #check
   if mode=="single" and not id:return error("id missing")
   #logic
   if mode=="single":await message_delete_user_single(postgres_client,request.state.user["id"],id)
   if mode=="created":await message_delete_user_created(postgres_client,request.state.user["id"])
   if mode=="received":await message_delete_user_received(postgres_client,request.state.user["id"])
   if mode=="all":await message_delete_user_all(postgres_client,request.state.user["id"])
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns")
async def public_otp_send_mobile_sns(request:Request):
   #param
   object=await request.json()
   mobile=object.get("mobile")
   template_id=object.get("template_id")
   message=object.get("message")
   entity_id=object.get("entity_id")
   sender_id=object.get("sender_id")
   if not mobile:return error("mobile missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,None,mobile)
   #logic
   if template_id:await send_message_template_sns(sns_client,mobile,message.replace("{otp}",str(otp)),entity_id,template_id,sender_id)
   else:sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def public_otp_send_mobile_fast2sms(request:Request):
   #param
   object=await request.json()
   mobile=object.get("mobile")
   if not mobile:return error("mobile missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,None,mobile)
   #logic
   response=requests.get("https://www.fast2sms.com/dev/bulkV2",params={"authorization":fast2sms_key,"numbers":mobile,"variables_values":otp,"route":"otp"})
   #final
   return {"status":1,"message":response.json()}

@app.post("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request):
   #param
   object=await request.json()
   email=object.get("email")
   sender_email=object.get("sender_email")
   if not email or not sender_email:return error("email/sender_email missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,email,None)
   #logic
   await send_email_ses(ses_client,sender_email,[email],"your otp code",str(otp))
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def public_otp_send_email_resend(request:Request):
   #param
   object=await request.json()
   email=object.get("email")
   sender_email=object.get("sender_email")
   if not email or not sender_email:return error("email/sender_email missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,email,None)
   #logic
   await send_email_resend(resend_key,"https://api.resend.com/emails",sender_email,[email],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def public_otp_verify_email(request:Request):
   #param
   object=await request.json()
   otp=object.get("otp")
   email=object.get("email")
   if not otp or not email:return error("otp/email missing")
   #logic
   await verify_otp(postgres_client,otp,email,None)
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def public_otp_verify_mobile(request:Request):
   #param
   object=await request.json()
   otp=object.get("otp")
   mobile=object.get("mobile")
   if not otp or not mobile:return error("otp/mobile missing")
   #logic
   await verify_otp(postgres_client,otp,None,mobile)
   #final
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if not table:return error("table missing")
   #check
   if table not in table_allowed_public_create.split(","):return error("table not allowed")
   #logic
   output=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   #final
   return {"status":1,"message":output}

@app.get("/public/object-read")
@cache(expire=100)
async def public_object_read(request:Request):
   #param
   object=request.query_params
   table=object.get("table")
   creator_data=object.get("creator_data")
   if not table:return error("table missing")
   #check
   if table not in table_allowed_public_read.split(","):return error("table not allowed")
   #logic
   if postgres_client_read_replica:object_list=await postgres_read(table,object,postgres_client_read_replica,postgres_column_datatype,object_serialize,create_where_string)
   else:object_list=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   #add creator data
   if creator_data and object_list:object_list=await add_creator_data(postgres_client,object_list,creator_data)
   #final
   return {"status":1,"message":object_list}

@app.post("/public/openai-prompt")
async def public_openai_prompt(request:Request):
   #param
   object=await request.json()
   model=object.get("model")
   prompt=object.get("prompt")
   is_web_search=int(object.get("is_web_search",0))
   previous_response_id=object.get("previous_response_id")
   if not model or not prompt:return error("model/prompt missing")
   #logic
   output=await openai_prompt(openai_client,model,prompt,is_web_search,previous_response_id)
   #final
   return {"status":1,"message":output}

@app.post("/public/openai-ocr")
async def public_openai_ocr(request:Request):
   #param
   object,file_list=await form_data_read(request)
   model=object.get("model")
   prompt=object.get("prompt")
   if not model or not prompt or not file_list:return error("model/prompt/file missing")
   #logic
   output=await openai_ocr(openai_client,model,prompt,file_list[-1])
   #final
   return {"status":1,"message":output}

@app.post("/public/gsheet-create")
async def public_gsheet_create(request:Request):
   #param
   spreadsheet_id=request.query_params.get("spreadsheet_id")
   sheet_name=request.query_params.get("sheet_name")
   object=await request.json()
   if not spreadsheet_id or not sheet_name:return error("spreadsheet_id/sheet_name missing")
   #logic
   output=await gsheet_create(gsheet_client,spreadsheet_id,sheet_name,object)
   #final
   return {"status":1,"message":output}

@app.get("/public/gsheet-read-service-account")
async def public_gsheet_read_service_account(request:Request):
   #param
   spreadsheet_id=request.query_params.get("spreadsheet_id")
   sheet_name=request.query_params.get("sheet_name")
   cell_boundary=request.query_params.get("cell_boundary")
   if not spreadsheet_id or not sheet_name:return error("spreadsheet_id/sheet_name missing")
   #logic
   output=await gsheet_read_service_account(gsheet_client,spreadsheet_id,sheet_name,cell_boundary)
   #final
   return {"status":1,"message":output}

@app.get("/public/gsheet-read-direct")
async def public_gsheet_read_direct(request:Request):
   #param
   spreadsheet_id=request.query_params.get("spreadsheet_id")
   gid=request.query_params.get("gid")
   if not spreadsheet_id or not gid:return error("spreadsheet_id/gid missing")
   #logic
   output=await gsheet_read_pandas(spreadsheet_id,gid)
   #final
   return {"status":1,"message":output}

cache_public_info={}
@app.get("/public/info")
async def public_info(request:Request):
   #variable
   global cache_public_info
   #logic
   if not cache_public_info or (time.time()-cache_public_info.get("set_at")>=1000):
      cache_public_info={
      "set_at":time.time(),
      "api_list":[route.path for route in request.app.routes],
      "redis":await redis_client.info() if redis_client else None,
      "postgres_schema":postgres_schema,
      "postgres_column_datatype":postgres_column_datatype,
      "users_api_access_count":len(users_api_access),
      "users_is_active_count":len(users_is_active),
      "bucket":s3_client.list_buckets() if s3_client else None,
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True))
      }
   #final
   return {"status":1,"message":cache_public_info}

@app.get("/public/page/{filename}")
async def public_page(filename:str):
   #variable
   file_path=os.path.join(".",f"{filename}.html")
   #check
   if ".." in filename or "/" in filename:return error("invalid filename")
   if not os.path.isfile(file_path):return error ("file not found")
   #logic
   with open(file_path, "r", encoding="utf-8") as file:html_content=file.read()
   #final
   return responses.HTMLResponse(content=html_content)

@app.get("/private/object-read")
@cache(expire=100)
async def private_object_read(request:Request):
   #param
   object=request.query_params
   table=object.get("table")
   if not table:return error("table missing")
   #check
   if table not in table_allowed_private_read.split(","):return error("table not allowed")
   #logic
   output=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   #final
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-direct")
async def private_file_upload_s3_direct(request:Request):
   #param
   object,file_list=await form_data_read(request)
   bucket=object.get("bucket")
   key=object.get("key")
   if not bucket or not file_list:return error("bucket/file missing")
   #variable
   key_list=None
   if key:key_list=key.split("---")
   #logic
   output=await s3_file_upload_direct(s3_client,s3_region_name,bucket,key_list,file_list)
   #final
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   #param
   object=await request.json()
   bucket=object.get("bucket")
   key=object.get("key")
   if not bucket or not key:return error("bucket/key missing")
   #logic
   output=await s3_file_upload_presigned(s3_client,s3_region_name,bucket,key,1000,100)
   #final
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def admin_object_create(request:Request):
   #param
   object=await request.json()
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   if not table:return error("table missing")
   #modify
   if postgres_schema.get(table).get("created_by_id"):object["created_by_id"]=request.state.user["id"]
   #logic
   output=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   #final
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if not table:return error("table missing")
   #modify
   if postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   #check
   if "id" not in object:return error ("id missing")
   if len(object)<=2:return error ("object length issue")
   #logic
   output=await postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   #final
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   del object["table"]
   del object["ids"]
   key,value=next(reversed(object.items()),(None, None))
   if not table or not ids or not key:return error("table/ids/key must")
   #logic
   await postgres_update_ids(postgres_client,table,ids,key,value,request.state.user["id"],None)
   #final
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   if not table or not ids:return error("table/ids must")
   #logic
   await postgres_delete_ids(postgres_client,table,ids,None)
   #final
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
@cache(expire=60)
async def admin_object_read(request:Request):
   #param
   object=request.query_params
   table=object.get("table")
   if not table:return error("table missing")
   #logic
   output=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   #final
   return {"status":1,"message":output}

@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   #param
   query=(await request.json()).get("query")
   if not query:return error("query must")
   #logic
   output=await postgres_query_runner(postgres_client,query,request.state.user["id"])
   #final
   return {"status":1,"message":output}

#fastapi
import sys,asyncio,uvicorn
async def main_fastapi():
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info",reload=True)
   server=uvicorn.Server(config)
   await server.serve()
if __name__=="__main__" and len(sys.argv)==1:
   try:asyncio.run(main_fastapi())
   except KeyboardInterrupt:print("exit")
   
#kafka
import sys,asyncio,json
async def main_kafka():
   postgres_client=await postgres_client_read(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   kafka_consumer_client=await kafka_consumer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name)
   try:
      async for message in kafka_consumer_client:
         if message.topic==channel_name:
            data=json.loads(message.value.decode('utf-8'))
            try:
               if data["mode"]=="create":output=await postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)   
               if data["mode"]=="update":output=await postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               print(output)
            except Exception as e:print(str(e))
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await kafka_consumer_client.stop()
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="kafka":
    try:asyncio.run(main_kafka())
    except KeyboardInterrupt:print("exit")

#redis
import sys,asyncio,json
async def main_redis():
   postgres_client=await postgres_client_read(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   redis_client,redis_pubsub=await redis_pubsub_read(redis_url,channel_name)
   try:
      async for message in redis_pubsub.listen():
         if message["type"]=="message" and message["channel"]==b'ch1':
            data=json.loads(message['data'])
            try:
               if data["mode"]=="create":output=await postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               if data["mode"]=="update":output=await postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               print(output)
            except Exception as e:print(str(e))
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await redis_pubsub.unsubscribe(channel_name)
      await redis_client.aclose()
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="redis":
    try:asyncio.run(main_redis())
    except KeyboardInterrupt:print("exit")
    
#aqmp callback
import json,asyncio,nest_asyncio
nest_asyncio.apply()
def aqmp_callback(ch,method,properties,body):
   data=json.loads(body)
   loop=asyncio.get_event_loop()
   try:
      if data["mode"]=="create":output=loop.run_until_complete(postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize))
      if data["mode"]=="update":output=loop.run_until_complete(postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize))
      print(output)
   except Exception as e:print(e.args)
   return None

#rabbitmq
import sys,asyncio
async def main_rabbitmq():
   global postgres_client,postgres_column_datatype
   postgres_client=await postgres_client_read(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   rabbitmq_client,rabbitmq_channel=await rabbitmq_client_read(rabbitmq_url,channel_name)
   try:
      rabbitmq_channel.basic_consume(channel_name,aqmp_callback,auto_ack=True)
      rabbitmq_channel.start_consuming()
   except KeyboardInterrupt:
      await postgres_client.disconnect()
      rabbitmq_channel.close()
      rabbitmq_client.close()
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="rabbitmq":
    try:asyncio.run(main_rabbitmq())
    except KeyboardInterrupt:print("exit")
    
#lavinmq
import sys,asyncio
async def main_lavinmq():
   global postgres_client,postgres_column_datatype
   postgres_client=await postgres_client_read(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   lavinmq_client,lavinmq_channel=await lavinmq_client_read(lavinmq_url,channel_name)
   try:
      lavinmq_channel.basic_consume(channel_name,aqmp_callback,auto_ack=True)
      lavinmq_channel.start_consuming()
   except KeyboardInterrupt:
      await postgres_client.disconnect()
      lavinmq_channel.close()
      lavinmq_client.close()
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="lavinmq":
    try:asyncio.run(main_lavinmq())
    except KeyboardInterrupt:print("exit")