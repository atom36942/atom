#function
from function import *

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
is_signup=int(os.getenv("is_signup",0))
postgres_url_read=os.getenv("postgres_url_read")
channel_name=os.getenv("channel_name","ch1")
user_type_allowed=[int(x) for x in os.getenv("user_type_allowed","1,2,3").split(",")]
column_disabled_non_admin=os.getenv("column_disabled_non_admin","is_active,is_verified,api_access").split(",")
postgres_url_read_replica=os.getenv("postgres_url_read_replica")
router_list=os.getenv("router_list").split(",") if os.getenv("router_list") else []

#variable
api_id={
"/admin/db-runner":1,
"/admin/user-create":2,
"/admin/object-create":3,
"/admin/user-update":4,
"/admin/object-update":5,
"/admin/ids-update":6,
"/admin/ids-delete":7,
"/admin/object-read":8
}
postgres_schema_default={
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
"type-smallint-0-btree",
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
"type-smallint-1-btree",
"username-text-0-btree",
"password-text-0-btree",
"google_id-text-0-btree",
"google_data-jsonb-0-0",
"email-text-0-btree",
"mobile-text-0-btree",
"api_access-text-0-0",
"last_active_at-timestamptz-0-0"
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
],
"bookmark_workseeker":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"workseeker_id-bigint-1-btree"
],
"work_profile":[
"title-text-1-0"
],
"workseeker":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-btree",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_deleted-smallint-0-btree",
"type-smallint-0-btree",
"work_profile_id-int-0-btree",
"experience-numeric(10,1)-0-btree",
"skill-text-0-0",
"description-text-0-0",
"salary_currency-text-0-0",
"salary_current-int-0-0",
"salary_expected-int-0-0",
"notice_period-smallint-0-0",
"college-text-0-0",
"degree-text-0-0",
"industry-text-0-0",
"certification-text-0-0",
"achievement-text-0-0",
"hobby-text-0-0",
"life_goal-text-0-0",
"strong_point-text-0-0",
"weak_point-text-0-0",
"name-text-0-0",
"gender-text-0-0",
"date_of_birth-date-0-0",
"nationality-text-0-0",
"language-text-0-0",
"email-text-0-0",
"mobile-text-0-0",
"country-text-0-0",
"state-text-0-0",
"city-text-0-0",
"current_location-text-0-0",
"is_remote-smallint-0-0",
"linkedin_url-text-0-0",
"github_url-text-0-0",
"portfolio_url-text-0-0",
"website_url-text-0-0",
"resume_url-text-0-0"
]
},
"query":{
"drop_all_index":"0 DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'index_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;",
"default_created_at":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='created_at' AND table_schema='public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"default_updated_at_1":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';",
"default_updated_at_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected=1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"delete_disable_bulk_1":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;",
"delete_disable_bulk_2":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"log_password_1":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;",
"log_password_2":"CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"root_user_1":"insert into users (type,username,password,api_access) values (1,'atom','5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5','1,2,3,4,5,6,7,8,9,10') on conflict do nothing;",
"root_user_2":"create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"default_1":"0 alter table users alter column is_active set default 1;",
"unique_1":"alter table users add constraint constraint_unique_users_type_username unique (type,username);",
"unique_2":"alter table users add constraint constraint_unique_users_type_email unique (type,email);",
"unique_3":"alter table users add constraint constraint_unique_users_type_mobile unique (type,mobile);",
"unique_4":"alter table users add constraint constraint_unique_users_type_google_id unique (type,google_id);",
"unique_5":"alter table workseeker add constraint constraint_unique_created_by_id unique (created_by_id);",
"unique_6":"alter table report_user add constraint constraint_unique_report_user unique (created_by_id,user_id);",
"unique_7":"alter table bookmark_workseeker add constraint constraint_unique_bookmark_workseeker unique (created_by_id,workseeker_id);",
"check_1":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"check_2":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_active' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_active', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_active IN (0,1) OR is_active IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;"
}
}

#globals
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

#sentry
if sentry_dsn:sentry_init(sentry_dsn)

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
      #users api access
      global users_api_access
      if postgres_schema.get("users"):users_api_access=await users_api_access_read(postgres_client_asyncpg,100000)
      #users is_active
      global users_is_active
      if postgres_schema.get("users"):users_is_active=await users_is_active_read(postgres_client_asyncpg,100000)
      #redis client
      global redis_client
      if redis_url:redis_client=await redis_client_read(redis_url)
      #valkey client
      global valkey_client
      if valkey_url:valkey_client=await redis_client_read(valkey_url)
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
      #ratelimiter init
      if redis_client:await ratelimiter_init(redis_client)
      #cache init
      if valkey_client:await cache_init(valkey_client,redis_key_builder)
      elif redis_url:await cache_init(redis_client,redis_key_builder)
      #app close
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
   except Exception as e:print(e.args)

#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#middleware
from fastapi import Request
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request:Request,api_function):
   try:
      start=time.time()
      #token check
      response=await token_check(request,key_root,key_jwt)
      if response["status"]==0:return error(response["message"])
      request.state.user=response["message"]
      #admin check
      if "admin/" in request.url.path:
         response=await admin_check(request.state.user["id"],api_id[request.url.path],users_api_access,postgres_client)
         if response["status"]==0:return error(response["message"])
      #is_active check
      for item in ["admin/","private","my/object-create"]:
         if item in request.url.path:
            response=await is_active_check(request.state.user["id"],users_is_active,postgres_client)
            if response["status"]==0:return error(response["message"])
      #api response
      if request.query_params.get("is_background")=="1":response=await api_response_background(request,api_function)
      else:response=await api_function(request)
      #api log
      object={"created_by_id":request.state.user.get("id",None),"api":request.url.path,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000}
      asyncio.create_task(batch_create_log_api(object,30,postgres_create,postgres_client,postgres_column_datatype,object_serialize))
   except Exception as e:
      print(traceback.format_exc())
      response=error(str(e.args))
   #final
   return response

#router
router_add(router_list,app)

#api import
from fastapi import Request,Depends,BackgroundTasks
import hashlib,json,time,os,random,asyncio
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter

#index
@app.get("/")
async def index():
   return {"status":1,"message":"welcome to atom"}

#root
@app.post("/root/db-init")
async def root_db_init(request:Request):
   #param
   mode=request.query_params.get("mode")
   if not mode:return error("mode missing")
   #variable
   if mode=="default":config=postgres_schema_default
   elif mode=="custom":config=await request.json()
   #logic
   response=await postgres_schema_init(postgres_client,postgres_schema_read,config)
   #final
   return response

@app.put("/root/reset-global")
async def root_reset_global():
   #postgres schema
   global postgres_schema
   postgres_schema=await postgres_schema_read(postgres_client)
   #postgres column datatype
   global postgres_column_datatype
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   #users api access
   global users_api_access
   if postgres_schema.get("users"):users_api_access=await users_api_access_read(postgres_client_asyncpg,100000)
   #users is_active
   global users_is_active
   if postgres_schema.get("users"):users_is_active=await users_is_active_read(postgres_client_asyncpg,100000)
   #final
   return {"status":1,"message":"done"}

@app.put("/root/db-checklist")
async def root_db_checklist():
   #logic
   await postgres_client.execute(query="update users set is_active=1,is_deleted=null where id=1;",values={})
   #final
   return {"status":1,"message":"done"}

@app.post("/root/db-uploader")
async def root_db_uploader(request:Request):
   #param
   form_data_key,form_data_file=await form_data_read(request)
   mode=form_data_key.get("mode")
   table=form_data_key.get("table")
   is_serialize=int(form_data_key.get("is_serialize",1))
   if not mode or not table or not form_data_file:return error("mode/table/file missing")
   #object list
   object_list=await file_to_object_list(form_data_file[-1])
   #logic
   if mode=="create":response=await postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="update":response=await postgres_update(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="delete":response=await postgres_delete(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/root/redis-uploader")
async def root_redis_uploader(request:Request):
   #param
   form_data_key,form_data_file=await form_data_read(request)
   table=form_data_key.get("table")
   expiry=form_data_key.get("expiry")
   if not table or not form_data_file:return error("table/file missing")
   #object list
   object_list=await file_to_object_list(form_data_file[-1])
   #logic
   await redis_object_create(table,object_list,expiry,valkey_client)
   #final
   return {"status":1,"message":"done"}

@app.delete("/root/redis-reset")
async def root_reset_redis():
   #logic
   if redis_client:await redis_client.flushall()
   if valkey_client:await valkey_client.flushall()
   #final
   return {"status":1,"message":"done"}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   #param
   url=request.query_params.get("url")
   if not url:return error("url missing")
   #logic
   for item in url.split("---"):output=await s3_url_delete(item,s3_resource)
   #final
   return {"status":1,"message":output}

@app.get("/root/s3-bucket-list")
async def root_s3_bucket_list():
   #logic
   output=s3_client.list_buckets()
   #final
   return {"status":1,"message":output}

@app.post("/root/s3-bucket-ops")
async def root_s3_bucket_ops(request:Request):
   #param
   mode=request.query_params.get("mode")
   bucket=request.query_params.get("bucket")
   if not mode or not bucket:return error("mode/bucket missing")
   #logic
   if mode=="create":output=s3_client.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})
   if mode=="public":
      s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
      policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
      output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   if mode=="empty":output=s3_resource.Bucket(bucket).objects.all().delete()
   if mode=="delete":output=s3_client.delete_bucket(Bucket=bucket)
   #final
   return {"status":1,"message":output}

#auth
@app.post("/auth/signup-username-password",dependencies=[Depends(RateLimiter(times=1,seconds=1))])
async def auth_signup_username_password(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return error("type/username/password missing")
   #convert
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #check
   if is_signup==0:return error("signup disabled")
   if type not in user_type_allowed:return error("wrong type")
   #logic
   query="insert into users (type,username,password) values (:type,:username,:password) returning *;"
   values={"type":type,"username":username,"password":password}
   output=await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":output}

@app.post("/auth/login-password-username")
async def auth_login_password_username(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return error("type/username/password missing")
   #convert
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #read user
   query=f"select * from users where type=:type and username=:username and password=:password order by id desc limit 1;"
   values={"type":type,"username":username,"password":password}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return error("user not found")
   #token create
   token=await token_create(key_jwt,user)
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
   #convert
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #read user
   query=f"select * from users where type=:type and email=:email and password=:password order by id desc limit 1;"
   values={"type":type,"email":email,"password":password}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return error("user not found")
   #token create
   token=await token_create(key_jwt,user)
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
   #convert
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #read user
   query=f"select * from users where type=:type and mobile=:mobile and password=:password order by id desc limit 1;"
   values={"type":type,"mobile":mobile,"password":password}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return error("user not found")
   #token create
   token=await token_create(key_jwt,user)
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
   #otp verify
   response=await verify_otp(postgres_client,otp,email,None)
   if response["status"]==0:return error(response["message"])
   #read user
   query=f"select * from users where type=:type and email=:email order by id desc limit 1;"
   values={"type":type,"email":email}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   #user create
   if not user:
      query=f"insert into users (type,email) values (:type,:email) returning *;"
      values={"type":type,"email":email}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   #token create
   token=await token_create(key_jwt,user)
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
   #otp verify
   response=await verify_otp(postgres_client,otp,None,mobile)
   if response["status"]==0:return error(response["message"])
   #read user
   query=f"select * from users where type=:type and mobile=:mobile order by id desc limit 1;"
   values={"type":type,"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   #user create
   if not user:
      query=f"insert into users (type,mobile) values (:type,:mobile) returning *;"
      values={"type":type,"mobile":mobile}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   #token create
   token=await token_create(key_jwt,user)
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
   #verify
   response=verify_google_token(google_client_id,google_token)
   if response["status"]==0:return error(response["message"])
   google_user=response["message"]
   #read user
   query=f"select * from users where type=:type and google_id=:google_id order by id desc limit 1;"
   values={"type":type,"google_id":google_user["sub"]}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   #user create
   if not user:
      query=f"insert into users (type,google_id,google_data) values (:type,:google_id,:google_data) returning *;"
      values={"type":type,"google_id":google_user["sub"],"google_data":json.dumps(google_user)}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   #token create
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

#my
@app.get("/my/profile")
async def my_profile(request:Request):
   #logic
   response=await read_user(postgres_client,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   asyncio.create_task(update_user_last_active_at(postgres_client,request.state.user["id"]))
   #final
   return response

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   #read user
   response=await read_user(postgres_client,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   user=response["message"]
   #token create
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def my_account_delete(request:Request):
   #param
   mode=request.query_params.get("mode")
   if not mode:return error("mode missing")
   #check user
   response=await read_user(postgres_client,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   user=response["message"]
   if user["api_access"]:return error("not allowed as you have api_access")
   #logic
   if mode=="soft":await user_object_delete_soft(postgres_client,request.state.user["id"])
   elif mode=="hard":await user_object_delete_hard(postgres_client,request.state.user["id"])
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
   if table not in ["test","message","report_user","bookmark_workseeker","workseeker"]:return error("table not allowed")
   if len(object)<=1:return error ("object issue")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   #logic
   if not queue:
      response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
      if response["status"]==0:return error(response["message"])
      output=response["message"]
   elif queue:
      data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
      if queue=="redis":output=await redis_client.publish(channel_name,json.dumps(data))
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
   table=request.query_params.get("table")
   object=dict(request.query_params)
   if not table:return error("table missing")
   #modify
   object["created_by_id"]=f"=,{request.state.user['id']}"
   #logic
   response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   #final
   return response

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
   if otp:
      email,mobile=object.get("email"),object.get("mobile")
      response=await verify_otp(postgres_client,otp,email,mobile)
      if response["status"]==0:return error(response["message"])
   #logic
   response=await postgres_update("users",[object],1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

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
   response=await postgres_update_self(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   if not table or not ids:return error("table/ids must")
   #modify
   del object["table"]
   del object["ids"]
   #key value
   key,value=next(reversed(object.items()),(None, None))
   #check
   if table in ["users"]:return error("table not allowed")
   if not key:return error("column null issue")
   if key in column_disabled_non_admin:return error("column not allowed")
   #logic
   query=f"update {table} set {key}=:value,updated_by_id=:user_id where id in ({ids}) and created_by_id=:user_id;"
   values={"user_id":request.state.user["id"],"value":value}
   await postgres_client.execute(query=query,values=values)
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
   if table not in ["test","report_user","bookmark_workseeker"]:return error("table not allowed")
   #logic
   response=await postgres_delete_any(table,object,postgres_client,create_where_string,object_serialize,postgres_column_datatype)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   if not table or not ids:return error("table/ids must")
   #check
   if table not in ["test","report_user","bookmark_workseeker"]:return error("table not allowed")
   #logic
   query=f"delete from {table} where id in ({ids}) and created_by_id=:created_by_id;"
   values={"created_by_id":request.state.user["id"]}
   await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":"done"}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   table=request.query_params.get("table")
   parent_column=request.query_params.get("parent_column")
   parent_table=request.query_params.get("parent_table")
   if not table or not parent_column:return error("table/parent_column/parent_table missing")
   #logic
   response=await postgres_parent_read(table,parent_column,parent_table,postgres_client,order,limit,(page-1)*limit,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   is_unread=request.query_params.get("is_unread")
   #logic
   response=await message_inbox_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/my/message-received")
async def my_message_received(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   is_unread=request.query_params.get("is_unread")
   #logic
   response=await message_received_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   if response["status"]==0:return error(response["message"])
   object_list=response["message"]
   #mark message read
   if object_list:
      ids=','.join([str(item['id']) for item in object_list])
      asyncio.create_task(mark_message_read_ids(postgres_client,ids))
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   user_id=int(request.query_params.get("user_id",0))
   if not user_id:return error("user_id missing")
   #logic
   response=await message_thread_user(postgres_client,request.state.user["id"],user_id,order,limit,(page-1)*limit)
   if response["status"]==0:return error(response["message"])
   #mark message thread read
   asyncio.create_task(mark_message_read_thread(postgres_client,request.state.user["id"],user_id))
   #final
   return response

@app.delete("/my/message-delete")
async def my_message_delete(request:Request):
   #param
   mode=request.query_params.get("mode")
   id=int(request.query_params.get("id",0))
   if not mode:return error("mode missing")
   #check
   if mode=="single" and not id:return error("id missing")
   #logic
   await message_delete_user(postgres_client,request.state.user["id"],mode,id)
   #final
   return {"status":1,"message":"done"}

#public
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
      "api_id":api_id,
      "redis":await redis_client.info(),
      "postgres_schema":postgres_schema,
      "postgres_column_datatype":postgres_column_datatype,
      "users_api_access_count":len(users_api_access),
      "users_is_active_count":len(users_is_active),
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True)),
      "users_count":await postgres_client.fetch_all(query="select count(*) from users where is_active is distinct from 0;",values={}),
      }
   #final
   return {"status":1,"message":cache_public_info}

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
   response=await generate_otp(postgres_client,None,mobile)
   if response["status"]==0:return error(response["message"])
   otp=response["message"]
   #logic
   if template_id:await send_message_template_sns(sns_client,mobile,message.replace("{otp}",str(otp)),entity_id,template_id,sender_id)
   else:sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request):
   #param
   object=await request.json()
   email=object.get("email")
   sender_email=object.get("sender_email")
   if not email or not sender_email:return error("email/sender_email missing")
   #generate otp
   response=await generate_otp(postgres_client,email,None)
   if response["status"]==0:return error(response["message"])
   otp=response["message"]
   #logic
   await send_email_ses(ses_client,sender_email,[email],"otp from atom",str(otp))
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
   if table not in ["test"]:return error("table not allowed")
   #logic
   response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/public/object-read")
@cache(expire=100)
async def public_object_read(request:Request):
   #param
   table=request.query_params.get("table")
   object=request.query_params
   creator_data=request.query_params.get("creator_data")
   if not table:return error("table missing")
   #check
   if table not in ["test"]:return error("table not allowed")
   #logic
   if postgres_client_read_replica:response=await postgres_read(table,object,postgres_client_read_replica,postgres_column_datatype,object_serialize,create_where_string)
   else:response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   object_list=response["message"]
   #add creator data
   if object_list and creator_data:
      response=await add_creator_data(postgres_client,object_list,creator_data)
      if response["status"]==0:return response
      object_list=response["message"]
   #final
   return {"status":1,"message":object_list}

#private
@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   #param
   bucket=request.query_params.get("bucket")
   key=request.query_params.get("key")
   if not bucket or not key:return error("bucket/key missing")
   expiry_sec,size_kb=1000,100
   #check
   if "." not in key:return error("extension must")
   #logic
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec,Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   #final
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-direct")
async def private_file_upload_s3_direct(request:Request):
   #param
   form_data_key,form_data_file=await form_data_read(request)
   bucket=form_data_key.get("bucket")
   key=form_data_key.get("key")
   if not bucket or not key or not form_data_file:return error("bucket/key/file missing")
   key_list=None if key=="uuid" else key.split("---")
   #logic
   response=await s3_file_upload(s3_client,s3_region_name,bucket,key_list,form_data_file)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/private/object-read")
@cache(expire=100)
async def private_object_read(request:Request):
   #param
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=request.query_params
   #check
   if table not in ["test"]:return error("table not allowed")
   #logic
   response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/private/workseeker-read")
@cache(expire=100)
async def private_workseeker_read(request:Request):
   #pagination
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   #filter
   work_profile_id=int(request.query_params.get("work_profile_id")) if request.query_params.get("work_profile_id") else None
   experience_min=int(request.query_params.get("experience_min")) if request.query_params.get("experience_min") else None
   experience_max=int(request.query_params.get("experience_max")) if request.query_params.get("experience_max") else None
   skill=f"%{request.query_params.get('skill')}%" if request.query_params.get('skill') else None
   #logic
   query=f'''
   select * from workseeker where
   (work_profile_id=:work_profile_id or :work_profile_id is null) and
   (experience >= :experience_min or :experience_min is null) and
   (experience <= :experience_max or :experience_max is null) and
   (skill ilike :skill or :skill is null)
   order by {order} limit {limit} offset {(page-1)*limit};
   '''
   values={
   "work_profile_id":work_profile_id,
   "experience_min":experience_min,"experience_max":experience_max,
   "skill":skill
   }
   output=await postgres_client.fetch_all(query=query,values=values)
   #final
   return {"status":1,"message":output}

#admin
@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   #param
   query=(await request.json()).get("query")
   if not query:return error("query must")
   #check
   danger_word=["drop","truncate"]
   stop_word=["drop","delete","update","insert","alter","truncate","create", "rename","replace","merge","grant","revoke","execute","call","comment","set","disable","enable","lock","unlock"]
   must_word=["select"]
   for item in danger_word:
       if item in query.lower():return error(f"{item} keyword not allowed in query")
   if request.state.user["id"]!=1:
      for item in stop_word:
         if item in query.lower():return error(f"{item} keyword not allowed in query")
      for item in must_word:
         if item not in query.lower():return error(f"{item} keyword must be present in query")
   #logic
   output=await postgres_client.fetch_all(query=query,values={})
   #final
   return {"status":1,"message":output}

@app.post("/admin/user-create")
async def admin_user_create(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   if not type:return error("type missing")
   #check
   if type not in user_type_allowed:return error("wrong type")
   #logic
   response=await postgres_create("users",[object],1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/admin/user-update")
async def admin_user_update(request:Request):
   #param
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   #check
   if "id" not in object:return error ("id missing")
   if len(object)<=2:return error ("object length issue")
   if any(key in object and len(object)!=3 for key in ["password"]):return error("object length should be 2")
   #logic
   response=await postgres_update("users",[object],1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/admin/object-create")
async def admin_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   if not table:return error("table missing")
   object=await request.json()
   object["created_by_id"]=request.state.user["id"]
   #check
   if table not in ["test"]:return error("table not allowed")
   #logic
   response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   if not table:return error("table missing")
   #check
   if table in ["users"]:return error("table not allowed")
   if len(object)<=2:return error ("object issue")
   if "id" not in object:return error ("id missing")
   #logic
   response=await postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   #param
   table=request.query_params.get("table")
   ids=request.query_params.get("ids")
   if not table or not ids:return error("table/ids must")
   object=await request.json()
   key,value=next(reversed(object.items()),(None, None))
   #check
   if table in ["users"]:return error("table not allowed")
   if len(object)!=1:return error(" object length should be 1")
   #logic
   query=f"update {table} set {key}=:value,updated_by_id=:updated_by_id where id in ({ids});"
   values={"updated_by_id":request.state.user["id"],"value":object.get(key)}
   await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   #param
   table=request.query_params.get("table")
   ids=request.query_params.get("ids")
   if not table or not ids:return error("table/ids must")
   #check
   if table in ["users"]:return error("table not allowed")
   #logic
   query=f"delete from {table} where id in ({ids});"
   await postgres_client.execute(query=query,values={})
   #final
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
@cache(expire=60)
async def admin_object_read(request:Request):
   #param
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=request.query_params
   #logic
   response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   #final
   return response

#mode
import sys
mode=sys.argv

#fastapi
import asyncio,uvicorn
async def main_fastapi():
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info",reload=True)
   server=uvicorn.Server(config)
   await server.serve()
if __name__=="__main__" and len(mode)==1:
   try:asyncio.run(main_fastapi())
   except KeyboardInterrupt:print("exit")
   
#nest
import nest_asyncio
nest_asyncio.apply()

#redis
import asyncio,json
async def main_redis():
   postgres_client=await postgres_client_read(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   redis_client,redis_pubsub=await redis_client_pubsub_read(redis_url,channel_name)
   try:
      async for message in redis_pubsub.listen():
         if message["type"]=="message" and message["channel"]==b'ch1':
            data=json.loads(message['data'])
            try:
               if data["mode"]=="create":response=await postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               if data["mode"]=="update":response=await postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               print(response)
            except Exception as e:
               print(e.args)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await redis_pubsub.unsubscribe(channel_name)
      await redis_client.aclose()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="redis":
    try:asyncio.run(main_redis())
    except KeyboardInterrupt:print("exit")

#kafka
import asyncio,json
async def main_kafka():
   postgres_client=await postgres_client_read(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   kafka_consumer_client=await kafka_consumer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name)
   try:
      async for message in kafka_consumer_client:
         if message.topic==channel_name:
            data=json.loads(message.value.decode('utf-8'))
            try:
               if data["mode"]=="create":response=await postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)   
               if data["mode"]=="update":response=await postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               print(response)
            except Exception as e:
               print(e.args)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await kafka_consumer_client.stop()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="kafka":
    try:asyncio.run(main_kafka())
    except KeyboardInterrupt:print("exit")

#aqmp callback
def aqmp_callback(ch,method,properties,body):
   data=json.loads(body)
   loop=asyncio.get_event_loop()
   try:
      if data["mode"]=="create":response=loop.run_until_complete(postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize))
      if data["mode"]=="update":response=loop.run_until_complete(postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize))
      print(response)
   except Exception as e:
      print(e.args)
   return None

#rabbitmq
import asyncio,json
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
if __name__ == "__main__" and len(mode)>1 and mode[1]=="rabbitmq":
    try:asyncio.run(main_rabbitmq())
    except KeyboardInterrupt:print("exit")

#lavinmq
import asyncio,json
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
if __name__ == "__main__" and len(mode)>1 and mode[1]=="lavinmq":
    try:asyncio.run(main_lavinmq())
    except KeyboardInterrupt:print("exit")