#env
import os
from dotenv import load_dotenv
load_dotenv()

#function
from function import *

#globals
postgres_database_url=os.getenv("postgres_database_url")
redis_server_url=os.getenv("redis_server_url")
secret_key_root=os.getenv("secret_key_root")
secret_key_jwt=os.getenv("secret_key_jwt")
sentry_dsn=os.getenv("sentry_dsn")
rabbitmq_server_url=os.getenv("rabbitmq_server_url")
lavinmq_server_url=os.getenv("lavinmq_server_url")
kafka_path_cafile=os.getenv("kafka_path_cafile")
kafka_path_certfile=os.getenv("kafka_path_certfile")
kafka_path_keyfile=os.getenv("kafka_path_keyfile")
kafka_server_url=os.getenv("kafka_server_url")
aws_access_key_id=os.getenv("aws_access_key_id")
aws_secret_access_key=os.getenv("aws_secret_access_key")
sns_region_name=os.getenv("sns_region_name")
sns_region_name=os.getenv("sns_region_name")
ses_region_name=os.getenv("ses_region_name")
mongodb_cluster_url=os.getenv("mongodb_cluster_url")
postgres_client=None
postgres_schema={}
postgres_column_datatype={}
project_data={}
admin_data={}
redis_client=None
redis_pubsub=None
rabbitmq_client=None
rabbitmq_channel=None
lavinmq_client=None
lavinmq_channel=None
kafka_producer_client=None
kafka_consumer_client=None
s3_client=None
s3_resource=None
sns_client=None
ses_client=None
mongodb_client=None
object_list_log=[]
postgres_config_default={
"table":{
"atom":["type-text-0-0","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0"],
"project":["type-text-0-btree","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0"],
"users":["created_at-timestamptz-0-brin","created_by_id-bigint-0-btree","updated_at-timestamptz-0-0","updated_by_id-bigint-0-0","is_active-smallint-0-btree","is_protected-smallint-0-btree","type-text-0-btree","username-text-0-0","password-text-0-btree","location-geography(POINT)-0-gist","metadata-jsonb-0-0","google_id-text-0-btree","last_active_at-timestamptz-0-0","api_access-text-0-0","date_of_birth-date-0-0","email-text-0-btree","mobile-text-0-btree"],
"post":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","type-text-0-0","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0"],
"message":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","user_id-bigint-1-btree","description-text-0-0","is_read-smallint-0-btree"],
"helpdesk":["created_at-timestamptz-0-0","created_by_id-bigint-0-0","status-text-0-0","remark-text-0-0","description-text-0-0"],
"otp":["created_at-timestamptz-0-0","otp-integer-1-0","email-text-0-btree","mobile-text-0-btree"],
"log_api":["created_at-timestamptz-0-0","created_by_id-bigint-0-0","api-text-0-0","status_code-smallint-0-0","response_time_ms-numeric(1000,3)-0-0"],
"log_password":["created_at-timestamptz-0-0","user_id-bigint-0-0","password-text-0-0"],
"action_like":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_bookmark":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_report":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_block":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_follow":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_rating":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","rating-numeric(10,3)-0-0"],
"action_comment":["created_at-timestamptz-0-0","created_by_id-bigint-0-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","description-text-0-0"],
"human":["created_at-timestamptz-0-0","name-text-0-0"],
},
"query":{
"extension":"create extension if not exists postgis",
"unique":"alter table users add constraint constraint_unique_users_username unique (username);---alter table action_like add constraint constraint_unique_action_like_cpp unique (created_by_id,parent_table,parent_id);---alter table action_bookmark add constraint constraint_unique_action_bookmark_cpp unique (created_by_id,parent_table,parent_id);---alter table action_report add constraint constraint_unique_action_report_cpp unique (created_by_id,parent_table,parent_id);---alter table action_block add constraint constraint_unique_action_block_cpp unique (created_by_id,parent_table,parent_id);---alter table action_follow add constraint constraint_unique_action_follow_cpp unique (created_by_id,parent_table,parent_id);",
"default_created_at":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'created_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"default_updated_at":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';---DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'updated_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'is_protected' AND table_schema = 'public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected = 1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"delete_disable_bulk":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;---create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"log_password":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;---CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"root_user":"insert into users (username,password) values ('atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3') on conflict do nothing;---create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
}
}

#setters
from databases import Database
async def set_postgres_client():
   global postgres_client
   postgres_client=Database(os.getenv("postgres_database_url"),min_size=1,max_size=100)
   await postgres_client.connect()
   return None

async def set_postgres_schema():
   global postgres_schema,postgres_column_datatype
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return None

async def set_project_data():
   global project_data
   if postgres_schema.get("project",{}):[project_data.setdefault(object["type"],[]).append(object) for object in await postgres_client.fetch_all(query="select * from project limit 10000", values={})]
   return None

async def set_admin_data():
   global admin_data
   if postgres_schema.get("users",{}).get("api_access",{}):
      for object in await postgres_client.fetch_all(query="select id,api_access from users where api_access is not null limit 10000",values={}):admin_data[object["id"]]=object["api_access"]
   return None

import redis.asyncio as redis
async def set_redis_client():
   global redis_client,redis_pubsub
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(os.getenv("redis_server_url")))
   redis_pubsub=redis_client.pubsub()
   await redis_pubsub.subscribe("postgres_cud")
   return None

import boto3
async def set_aws_client():
   global s3_client,s3_resource,sns_client,ses_client
   if aws_access_key_id:s3_client=boto3.client("s3",aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   if aws_access_key_id:s3_resource=boto3.resource("s3",aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   if sns_region_name:sns_client=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   if ses_region_name:ses_client=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

import motor.motor_asyncio
async def set_mongodb_client():
   global mongodb_client
   if mongodb_cluster_url:mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(mongodb_cluster_url)
   return None

import pika
async def set_rabbitmq_client():
   global rabbitmq_client,rabbitmq_channel
   if rabbitmq_server_url:
      rabbitmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("rabbitmq_server_url")))
      rabbitmq_channel=rabbitmq_client.channel()
      rabbitmq_channel.queue_declare(queue="postgres_cud")
   return None

import pika
async def set_lavinmq_client():
   global lavinmq_client,lavinmq_channel
   if lavinmq_server_url:
      lavinmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("lavinmq_server_url")))
      lavinmq_channel=lavinmq_client.channel()
      lavinmq_channel.queue_declare(queue="postgres_cud")
   return None

from aiokafka import AIOKafkaProducer
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def set_kafka_client():
   global kafka_producer_client,kafka_consumer_client
   if kafka_server_url:
      context=create_ssl_context(cafile=os.getenv("kafka_path_cafile"),certfile=os.getenv("kafka_path_certfile"),keyfile=os.getenv("kafka_path_keyfile"))
      kafka_producer_client=AIOKafkaProducer(bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context)
      kafka_consumer_client=AIOKafkaConsumer("postgres_cud",bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
      await kafka_producer_client.start()
      await kafka_consumer_client.start()
   return None

#sentry
import sentry_sdk
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

#redis key builder
from fastapi import Request,Response
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param=str(dict(sorted(request.query_params.items())))
   user_id=0
   if "my/" in api:user_id=json.loads(jwt.decode(request.headers.get("Authorization").split(" ",1)[1],secret_key_jwt,algorithms="HS256")["data"])["id"]
   key=f"{api}---{query_param}---{str(user_id)}"
   return key

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_limiter import FastAPILimiter
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
@asynccontextmanager
async def lifespan(app:FastAPI):
   #setters
   await set_postgres_client()
   await set_postgres_schema()
   await set_project_data()
   await set_admin_data()
   await set_redis_client()
   await set_aws_client()
   await set_mongodb_client()
   await set_rabbitmq_client()
   await set_lavinmq_client()
   await set_kafka_client()
   #init
   await FastAPILimiter.init(redis_client)
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   #disconnect
   yield
   await postgres_client.disconnect()
   await redis_client.aclose()
   if rabbitmq_server_url:rabbitmq_channel.close(),rabbitmq_client.close()
   if lavinmq_server_url:lavinmq_channel.close(),lavinmq_client.close()
   if kafka_server_url:await kafka_producer_client.stop()

#fastapi
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#middleware
from fastapi import Request,responses
import time,traceback
from starlette.background import BackgroundTask
@app.middleware("http")
async def middleware(request:Request,api_function):
   start=time.time()
   api=request.url.path
   method=request.method
   query_param=dict(request.query_params)
   body=await request.body()
   token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
   try:
      #auth
      user={}
      if "root/" in api and token!=secret_key_root:return {"status":0,"message":"token root mismatch"}
      if any(item in api for item in ["my/", "private/", "admin/"]):user=json.loads(jwt.decode(token,secret_key_jwt,algorithms="HS256")["data"])
      if "admin/" in api:
         api_access_user=admin_data.get(user["id"],None)
         if not api_access_user or api not in api_access_user.split(","):return {"status":0,"message":"api access denied"}
      request.state.user=user
      #api response background
      if query_param.get("is_background",None)=="1":
         async def receive():return {"type":"http.request","body":body}
         async def api_function_new():
            reques_new=Request(scope=request.scope,receive=receive)
            await api_function(reques_new)
         response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
         response.background=BackgroundTask(api_function_new)
      #api response direct
      else:
         response=await api_function(request)
         status_code=response.status_code
         end=time.time()
         response_time_ms=(end-start)*1000
         #api log
         if "log_api" in postgres_schema:
            global object_list_log
            object={"created_by_id":user.get("id",None),"api":api,"status_code":status_code,"response_time_ms":response_time_ms}
            object_list_log.append(object)
            if len(object_list_log)>=3:
               response.background=BackgroundTask(postgres_cud,postgres_client,"create","log_api",object_list_log)
               object_list_log=[]
   #exception
   except Exception as e:
      print(traceback.format_exc())
      return responses.JSONResponse(status_code=400,content={"status":0,"message":str(e.args)})
   #final
   return response

#router
import os,glob
current_directory_path=os.path.dirname(os.path.realpath(__file__))
current_directory_file_path_list=glob.glob(f"{current_directory_path}/*")
current_directory_file_name_list=[item.rsplit("/",1)[-1] for item in current_directory_file_path_list]
current_directory_file_name_list_without_extension=[item.split(".")[0] for item in current_directory_file_name_list]
for item in current_directory_file_name_list_without_extension:
   if "api_" in item:
      router=__import__(item).router
      app.include_router(router)
      
#api
from fastapi import Request,UploadFile,responses,Depends,BackgroundTasks
import hashlib,datetime,json,time,jwt,csv,codecs,os,random
from io import BytesIO
from typing import Literal
from bson.objectid import ObjectId
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel

@app.get("/")
async def root():
   if project_data.get("index_html",None):response=responses.HTMLResponse(content=project_data["index_html"][0]["description"],status_code=200)
   else:response={"status":1,"message":"welcome to atom"}
   return response

@app.post("/root/postgres-schema-init")
async def root_postgres_schema_init(request:Request,mode:str):
   if mode=="default":config=postgres_config_default
   if mode=="self":config=await request.json()
   await postgres_schema_init(postgres_client,config)
   return {"status":1,"message":"done"}

@app.get("/root/grant-api-access-all")
async def root_grant_api_access_all(request:Request,user_id:int):
   api_list=[route.path for route in request.app.routes]
   api_list_admin=[item for item in api_list if "/admin" in item]
   query="update users set api_access=:api_access where id=:id returning *"
   query_param={"id":user_id,"api_access":",".join(api_list_admin)}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.get("/root/postgres-clean")
async def root_pclean():
   #creator null
   for table,column in postgres_schema.items():
      if column.get("created_by_id",None):
         query=f"delete from {table} where created_by_id not in (select id from users);"
         await postgres_client.execute(query=query,values={})
   #parent null
   for table,column in postgres_schema.items():
      if column.get("parent_table",None) and column.get("parent_id",None):
         output=await postgres_client.fetch_all(query=f"select distinct(parent_table) from {table};",values={})
         parent_table_list=[item['parent_table'] for item in output]
         for item in parent_table_list:
            query=f"delete from {table} where parent_table='{item}' and parent_id not in (select id from {item});"
            await postgres_client.execute(query=query,values={})
   #misc
   await postgres_client.execute(query="update users set api_access=null where length(api_access)<5;",values={})
   await postgres_client.execute(query="truncate table log_api;",values={})
   #final
   return {"status":1,"message":"done"}

@app.get("/root/postgres-query-runner")
async def root_postgres_query_runner(query:str):
   query_list=query.split("---")
   if len(query_list)==1:output=await postgres_client.fetch_all(query=query,values={})
   else:
      transaction=await postgres_client.transaction()
      try:output=[(await postgres_client.fetch_all(query=item,values={})) for item in query_list]
      except Exception as e:
         await transaction.rollback()
         return responses.JSONResponse(status_code=400,content={"status":0,"message":e.args})
      else:
         await transaction.commit()
   return {"status":1,"message":output}

@app.get("/root/reset-global")
async def root_reset_global():
   await set_postgres_schema()
   await set_project_data()
   await set_admin_data()
   return {"status":1,"message":"done"}

@app.get("/auth/signup",dependencies=[Depends(RateLimiter(times=1,seconds=3))])
async def auth_signup(username:str,password:str):
   query="insert into users (username,password) values (:username,:password) returning *;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.get("/auth/login")
async def auth_login(request:Request):
   query_param=dict(request.query_params)
   mode,username,password,google_id,email,mobile,otp=query_param.get("mode",None),query_param.get("username",None),query_param.get("password",None),query_param.get("google_id",None),query_param.get("email",None),query_param.get("mobile",None),query_param.get("otp",None)
   #verify otp
   if otp:
      if email:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;",values={"email":email})
      if mobile:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;",values={"mobile":mobile})
      if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
      if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #read user
   if mode=="up":
      output=await postgres_client.fetch_all(query="select id from users where username=:username and password=:password order by id desc limit 1;",values={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()})
      if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
      user=output[0] if output else None
   if mode=="g":
      if not google_id:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wromg param"})
      output=await postgres_client.fetch_all(query="select id from users where google_id=:google_id order by id desc limit 1;",values={"google_id":hashlib.sha256(google_id.encode()).hexdigest()})
      if not output:output=await postgres_client.fetch_all(query="insert into users (google_id) values (:google_id) returning *;",values={"google_id":hashlib.sha256(query_param.get("google_id",None).encode()).hexdigest()})
      user=output[0] if output else None
   if mode=="eo":
      if not email:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wromg param"})
      output=await postgres_client.fetch_all(query="select id from users where email=:email order by id desc limit 1;",values={"email":email})
      if not output:output=await postgres_client.fetch_all(query="insert into users (email) values (:email) returning *;",values={"email":email})
      user=output[0] if output else None
   if mode=="mo":
      if not mobile:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wromg param"})
      output=await postgres_client.fetch_all(query="select id from users where mobile=:mobile order by id desc limit 1;",values={"mobile":mobile})
      if not output:output=await postgres_client.fetch_all(query="insert into users (mobile) values (:mobile) returning *;",values={"mobile":mobile})
      user=output[0] if output else None
   if mode=="ep":
      output=await postgres_client.fetch_all(query="select * from users where email=:email and password=:password order by id desc limit 1;",values={"email":email,"password":hashlib.sha256(password.encode()).hexdigest()})
      if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
      user=output[0] if output else None
   if mode=="mp":
      output=await postgres_client.fetch_all(query="select * from users where mobile=:mobile and password=:password order by id desc limit 1;",values={"mobile":mobile,"password":hashlib.sha256(password.encode()).hexdigest()})
      if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
      user=output[0] if output else None
   #create token
   data=json.dumps({"id":user["id"]},default=str)
   token=jwt.encode({"exp":time.time()+1000000000000,"data":data},secret_key_jwt)
   #final
   return {"status":1,"message":token}









@app.get("/my/profile")
async def my_profile(request:Request,background:BackgroundTasks):
   #read user
   query="select * from users where id=:id;"
   query_param={"id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #update last active at
   query="update users set last_active_at=:last_active_at where id=:id"
   query_param={"id":user["id"],"last_active_at":datetime.datetime.now()}
   background.add_task(postgres_client.execute,query=query,values=query_param)
   #final
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   #read user
   query="select * from users where id=:id;"
   query_param={"id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create token
   response=await create_token(user,secret_key_jwt)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
   #final
   return {"status":1,"message":token}

@app.put("/my/update-password")
async def my_update_password(request:Request,password:str):
   query="update users set password=:password,updated_by_id=:updated_by_id where id=:id returning *;"
   query_param={"id":request.state.user["id"],"password":hashlib.sha256(password.encode()).hexdigest(),"updated_by_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.put("/my/update-email")
async def my_update_email(request:Request,otp:int,email:str):
   #verify otp
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
   query_param={"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #logic
   query="update users set email=:email,updated_by_id=:updated_by_id where id=:id returning *;"
   query_param={"id":request.state.user["id"],"email":email,"updated_by_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.put("/my/update-mobile")
async def my_update_mobile(request:Request,otp:int,mobile:str):
   #verify otp
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
   query_param={"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #logic
   query="update users set mobile=:mobile,updated_by_id=:updated_by_id where id=:id returning *;"
   query_param={"id":request.state.user["id"],"mobile":mobile,"updated_by_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.delete("/my/delete-ids")
async def my_delete_ids(request:Request,table:str,ids:str):
   #check      
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if len(ids.split(","))>100:return responses.JSONResponse(status_code=400,content={"status":0,"message":"max 100 ids allowed"})
   #logic
   query=f"delete from {table} where created_by_id=:created_by_id and id in ({ids});"
   query_param={"created_by_id":request.state.user["id"]}
   await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def my_object_create(request:Request,table:str,is_serialize:int=1,queue:str=None):
   #object set
   object=await request.json()
   object["created_by_id"]=request.state.user["id"]
   #object keys check
   for k,v in object.items():
      if k in ["id","created_at","updated_at","updated_by_id","is_active","is_verified","is_deleted","password","google_id","otp"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{k} not allowed"})
   #object serialize
   if is_serialize and not queue:
      response=await object_serialize(postgres_column_datatype,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   if not queue:
      response=await postgres_cud(postgres_client,"create",table,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      output=response["message"]
   #logic queue
   if queue:
      output=await queue_push(queue,"postgres_cud",{"mode":"create","table":table,"object":object,"is_serialize":is_serialize},redis_client,rabbitmq_channel,lavinmq_channel,kafka_producer_client)
   #final
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request,table:str,is_serialize:int=1,queue:str=None):
   #object set
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   #object keys check
   for k,v in object.items():
      if k in ["created_at","created_by_id","is_active","is_verified","type","google_id","otp","api_access"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{k} not allowed"})
   if table=="users" and "email" in object:return responses.JSONResponse(status_code=400,content={"status":0,"message":"email not allowed"})
   if table=="users" and "mobile" in object:return responses.JSONResponse(status_code=400,content={"status":0,"message":"mobile not allowed"})
   #ownwership check
   response=await ownership_check(postgres_client,request.state.user["id"],table,object["id"])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #object serialize
   if is_serialize and not queue:
      response=await object_serialize(postgres_column_datatype,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   if not queue:
      response=await postgres_cud(postgres_client,"update",table,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      output=response["message"]
   #logic queue
   if queue:output=await queue_push(queue,"postgres_cud",{"mode":"update","table":table,"object":object,"is_serialize":is_serialize},redis_client,rabbitmq_channel,lavinmq_channel,kafka_producer_client)
   #final
   return {"status":1,"message":output}

@app.delete("/my/object-delete")
async def my_object_delete(request:Request,table:str,id:int,queue:str=None):
   #check
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   #ownwership check
   response=await ownership_check(postgres_client,request.state.user["id"],table,id)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #logic
   if not queue:
      query=f"delete from {table} where id=:id and created_by_id=:created_by_id;"
      query_param={"id":id,"created_by_id":request.state.user["id"]}
      output=await postgres_client.execute(query=query,values=query_param)
   #logic queue
   if queue:output=await queue_push(queue,"postgres_cud",{"mode":"delete","table":table,"object":{"id":id},"is_serialize":0},redis_client,rabbitmq_channel,lavinmq_channel,kafka_producer_client)
   #final
   return {"status":1,"message":output}

@app.get("/my/object-read")
@cache(expire=60)
async def my_object_read(request:Request,table:str,order:str="id desc",limit:int=100,page:int=1):
   #create where string
   query_param=dict(request.query_params)
   query_param["created_by_id"]=f"=,{request.state.user['id']}"
   response=await create_where_string(postgres_column_datatype,query_param)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   output=await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":output}

@app.delete("/my/object-delete-any")
async def my_object_delete_any(request:Request,table:str):
   #check
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   #create where string
   object_where=dict(request.query_params)
   object_where["created_by_id"]=f"=,{request.state.user['id']}"
   response=await create_where_string(postgres_column_datatype,object_where)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f"delete from {table} {where_string};"
   await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/delete-account")
async def my_delete_account(request:Request,mode:str=None):
   #read user
   query="select * from users where id=:id;"
   query_param={"id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #user check
   if user["id"]==1:return responses.JSONResponse(status_code=200,content={"status":0,"message":"root user cant be deleted"})
   if user["is_protected"]==1:return responses.JSONResponse(status_code=200,content={"status":0,"message":"protected user cant be deleted"})
   if user["api_access"]:return responses.JSONResponse(status_code=200,content={"status":0,"message":"admin user cant be deleted"})
   #logic
   if not mode:
      query="delete from users where id=:id;"
      query_param={"id":request.state.user["id"]}
      await postgres_client.fetch_all(query=query,values=query_param)
   if mode=="procedure":
      query=f"call procedure_delete_user({user['id']});"
      await postgres_client.fetch_all(query=query,values={})
   #final
   return {"status":1,"message":"account deleted"}

@app.post("/my/message-create")
async def my_message_create(request:Request,user_id:int,description:str,file_url:str=None):
   query=f"insert into message (created_by_id,user_id,description,file_url) values (:created_by_id,:user_id,:description,:file_url) returning *;"
   query_param={"created_by_id":request.state.user["id"],"user_id":user_id,"description":description,"file_url":file_url}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.get("/my/message-received")
async def my_message_received(request:Request,background:BackgroundTasks,order:str="id desc",limit:int=100,page:int=1,is_unread:int=None):
   #read message
   query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {(page-1)*limit};"
   if is_unread==1:query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #mark object read
   ids_list=[str(item["id"]) for item in output]
   ids_string=",".join(ids_list)
   if ids_string:
      query=f"update message set is_read=:is_read,updated_by_id=:updated_by_id where id in ({ids_string});"
      query_param={"is_read":1,"updated_by_id":request.state.user["id"]}
      background.add_task(postgres_client.execute,query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request,order:str="id desc",limit:int=100,page:int=1,is_unread:int=None):
   #read inbox
   query=f'''
   with
   x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),
   y as (select max(id) as id from x group by unique_id),
   z as (select m.* from y left join message as m on y.id=m.id)
   select * from z order by {order} limit {limit} offset {(page-1)*limit};
   '''
   if is_unread==1:query=f'''
   with
   x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),
   y as (select max(id) as id from x group by unique_id),
   z as (select m.* from y left join message as m on y.id=m.id),
   a as (select * from z where user_id=:user_id and is_read!=1 is null)
   select * from a order by {order} limit {limit} offset {(page-1)*limit};
   '''
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.get("/my/message-thread")
async def my_message_thread(request:Request,background:BackgroundTasks,user_id:int,order:str="id desc",limit:int=100,page:int=1):
   #read message thread
   query=f"select * from message where ((created_by_id=:user_1 and user_id=:user_2) or (created_by_id=:user_2 and user_id=:user_1)) order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_1":request.state.user["id"],"user_2":user_id}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #mark object read
   query="update message set is_read=:is_read,updated_by_id=:updated_by_id where created_by_id=:created_by_id and user_id=:user_id;"
   query_param={"is_read":1,"updated_by_id":request.state.user['id'],"created_by_id":user_id,"user_id":request.state.user["id"]}
   background.add_task(postgres_client.execute,query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.delete("/my/message-delete-single")
async def my_message_delete_single(request:Request,id:int):
   query="delete from message where id=:id and (created_by_id=:created_by_id or user_id=:user_id);;"
   query_param={"id":id,"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.delete("/my/message-delete-created")
async def my_message_delete_created(request:Request):
   query="delete from message where created_by_id=:created_by_id;"
   query_param={"created_by_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.delete("/my/message-delete-received")
async def my_message_delete_received(request:Request):
   query="delete from message where user_id=:user_id;"
   query_param={"user_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.delete("/my/message-delete-all")
async def my_message_delete_all(request:Request):
   query="delete from message where (created_by_id=:created_by_id or user_id=:user_id);"
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.post("/my/action-create")
async def my_action_create(request:Request,action:str):
   #object prepare
   object=dict(request.query_params)
   object["created_by_id"]=request.state.user["id"]
   del object["action"]
   #object serialize
   response=await object_serialize(postgres_column_datatype,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   object=response["message"][0]
   #object create
   response=await postgres_cud(postgres_client,"create",action,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

@app.get("/my/action-read-parent")
async def my_action_read_parent(request:Request,action:str,parent_table:str,order:str="id desc",limit:int=100,page:int=1):
   query=f'''
   with
   x as (select parent_id from {action} where created_by_id=:created_by_id and parent_table=:parent_table order by {order} limit {limit} offset {(page-1)*limit})
   select pt.* from x left join {parent_table} as pt on x.parent_id=pt.id;
   '''
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":output}

@app.delete("/my/action-delete-parent")
async def my_action_delete_parent(request:Request,action:str,parent_table:str,parent_id:int):
   query=f"delete from {action} where created_by_id=:created_by_id and parent_table=:parent_table and parent_id=:parent_id;"
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":"done"}

@app.get("/my/action-check-parent")
async def my_action_check_parent(request:Request,action:str,parent_table:str,parent_ids:str):
   #filter parent_ids
   query=f"select parent_id from {action} where parent_id in ({parent_ids}) and parent_table=:parent_table and created_by_id=:created_by_id;"
   query_param={"parent_table":parent_table,"created_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   parent_ids_output=[item["parent_id"] for item in output if item["parent_id"]]
   #parent_ids mapping
   parent_ids_input=parent_ids.split(",")
   parent_ids_input=[int(item) for item in parent_ids_input]
   mapping={item:1 if item in parent_ids_output else 0 for item in parent_ids_input}
   #final
   return {"status":1,"message":mapping}

@app.get("/my/action-on-me-creator-read")
async def my_action_on_me_creator_read(request:Request,action:str,order:str="id desc",limit:int=100,page:int=1):
   query=f'''
   with 
   x as (select * from {action} where parent_table=:parent_table),
   y as (select created_by_id from x where parent_id=:parent_id order by {order} limit {limit} offset {(page-1)*limit})
   select u.* from y left join users as u on y.created_by_id=u.id;
   '''
   query_param={"parent_table":"users","parent_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":output}

@app.get("/my/action-on-me-creator-read-mutual")
async def my_action_on_me_creator_read_mutual(request:Request,action:str,order:str="id desc",limit:int=100,page:int=1):
   query=f'''
   with 
   x as (select * from {action} where parent_table=:parent_table),
   y as (select created_by_id from {action} where created_by_id in (select parent_id from x where created_by_id=:created_by_id) and parent_id=:parent_id order by {order} limit {limit} offset {(page-1)*limit})
   select u.* from y left join users as u on y.created_by_id=u.id;
   '''
   query_param={"parent_table":"users","parent_id":request.state.user["id"],"created_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":output}

@app.get("/public/backend-info")
async def public_backend_info(request:Request,mode:str=None):
   #logic
   output={
   "postgres_schema":postgres_schema,
   "admin_data":admin_data,
   "api_list":[route.path for route in request.app.routes],
   "api_count":len([route.path for route in request.app.routes])-4,
   "redis":await redis_client.info()
   }
   #user variable
   globals_dict=globals()
   user_defined_variable={name:value for name,value in globals_dict.items() if not name.startswith("__")}
   user_defined_variable_size={f"{name} ({type(var).__name__})":sys.getsizeof(var)/1024 for name,var in user_defined_variable.items()}
   user_defined_variable_size=dict(sorted(user_defined_variable_size.items(), key=lambda item: item[1],reverse=True))
   output["user_variable"]=user_defined_variable_size
   #final
   if mode:output=output[mode]
   return {"status":1,"message":output}

@app.get("/public/verify-otp-email")
async def public_verify_otp_email(request:Request,email:str,otp:int):
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
   query_param={"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   return {"status":1,"message":"done"}

@app.get("/public/verify-otp-mobile")
async def public_verify_otp_mobile(request:Request,mobile:str,otp:int):
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
   query_param={"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request,table:Literal["helpdesk","human"],is_serialize:int=1):
   #object set
   object=await request.json()
   #serialize
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud(postgres_client,"create",table,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

@app.get("/public/object-read")
@cache(expire=60)
async def public_object_read(request:Request,table:Literal["users","post","atom","feed"],order:str="id desc",limit:int=100,page:int=1,location_filter:str=None,is_creator_data:int=0,action_count:str=None):
   #create where string
   query_param=dict(request.query_params)
   response=await create_where_string(postgres_column_datatype,query_param)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   if location_filter:
      long,lat,min_meter,max_meter=float(location_filter.split(",")[0]),float(location_filter.split(",")[1]),int(location_filter.split(",")[2]),int(location_filter.split(",")[3])
      query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   #addons
   #if is_creator_data==1:query=f'''with x as (select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit}) select x.*,u.username as created_by_id_username from x left join users as u on x.created_by_id=u.id order by x.id desc;'''
   if is_creator_data==1:
      response=await add_creator_data(postgres_client,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
   if action_count and "like" in action_count:
      response=await add_action_count(postgres_client,"action_like",table,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
   if action_count and "bookmark" in action_count:
      response=await add_action_count(postgres_client,"action_bookmark",table,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
   if action_count and "comment" in action_count:
      response=await add_action_count(postgres_client,"action_comment",table,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
   #final
   return {"status":1,"message":object_list}

@app.get("/private/object-read")
@cache(expire=60)
async def private_object_read(request:Request,table:Literal["users","post","atom"],order:str="id desc",limit:int=100,page:int=1):
   #create where string
   query_param=dict(request.query_params)
   response=await create_where_string(postgres_column_datatype,query_param)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   output=await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def admin_object_create(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   if postgres_schema[table].get("created_by_id",None):object["created_by_id"]=request.state.user["id"]
   #object serialize
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud(postgres_client,"create",table,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   output=response["message"]
   #final
   return {"status":1,"message":output}

@app.get("/admin/object-read")
@cache(expire=60)
async def admin_object_read(request:Request,table:str,order:str="id desc",limit:int=100,page:int=1):
   #create where string
   object_where=dict(request.query_params)
   response=await create_where_string(postgres_column_datatype,object_where)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #read object
   query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   output=await postgres_client.fetch_all(query=query,values=where_value)
   response={"status":1,"message":output}
   #final
   return response

@app.put("/admin/object-update")
async def admin_object_update(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   if postgres_schema[table].get("updated_by_id",None):object["updated_by_id"]=request.state.user["id"]
   #serialize
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud(postgres_client,"update",table,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

class schema_update_api_access(BaseModel):
   user_id:int
   api_access:str|None=None
@app.put("/admin/update-api-access")
async def admin_update_api_access(request:Request,body:schema_update_api_access):
   #api list
   api_list=[route.path for route in request.app.routes]
   api_list_admin=[item for item in api_list if "/admin" in item]
   #check body api access string
   if body.api_access:
      for item in body.api_access.split(","):
         if item not in api_list_admin:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wrong api access string"})
   #prepar eapi_access key
   if not body.api_access:api_access=None
   elif len(body.api_access)<=5:api_access=None
   else:api_access=body.api_access
   #logic
   query="update users set api_access=:api_access where id=:id returning *"
   query_param={"id":body.user_id,"api_access":api_access}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.put("/admin/delete-ids")
async def admin_delete_ids(request:Request,table:str,ids:str):
   query=f"delete from {table} where id in ({ids});"
   await postgres_client.execute(query=query,values={})
   return {"status":1,"message":"done"}

@app.post("/admin/csv-uploader")
async def admin_csv_uploader(request:Request,mode:str,table:str,file:UploadFile,is_serialize:int=1):
   #object list
   if file.content_type!="text/csv":return {"status":0,"message":"file extension must be csv"}
   file_csv=csv.DictReader(codecs.iterdecode(file.file,'utf-8'))
   object_list=[]
   for row in file_csv:object_list.append(row)
   file.file.close()
   #serialize
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
   #logic
   response=await postgres_cud(postgres_client,mode,table,object_list)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

@app.get("/admin/postgres-query-runner")
async def admin_postgres_query_runner(request:Request,query:str):
  for item in ["insert","update","delete","alter","drop"]:
    if item in query:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{item} not allowed in query"})
  output=await postgres_client.fetch_all(query=query,values={})
  return {"status":1,"message":output}

@app.get("/root/s3-list-all-bucket")
async def root_s3_list_all_bucket(request:Request):
   output=s3_client.list_buckets()
   return {"status":1,"message":output}

@app.post("/root/s3-create-bucket")
async def root_s3_create_bucket(request:Request,region:str,name:str):
   output=s3_client.create_bucket(Bucket=name,CreateBucketConfiguration={'LocationConstraint':region})
   return {"status":1,"message":output}

@app.put("/root/s3-make-bucket-public")
async def root_s3_make_bucket_public(request:Request,bucket:str):
   s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal": "*","Action": "s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return {"status":1,"message":output}

@app.delete("/root/s3-empty-bucket")
async def root_s3_empty_bucket(request:Request,bucket:str):
   output=s3_resource.Bucket(bucket).objects.all().delete()
   return {"status":1,"message":output}

@app.delete("/root/s3-delete-bucket")
async def root_s3_delete_bucket(request:Request,bucket:str):
   output=s3_client.delete_bucket(Bucket=bucket)
   return {"status":1,"message":output}

@app.post("/private/s3-upload-file")
async def private_s3_upload_file(request:Request,bucket:str,key:str,file:UploadFile):
   file_content=await file.read()
   file_stream=BytesIO(file_content)
   s3_client.upload_fileobj(file_stream,bucket,key)
   return {"status":1,"message":"done"}

@app.get("/private/s3-create-presigned-url")
async def private_s3_create_presigned_url(request:Request,bucket:str,key:str):
   expiry_sec,size_kb=1000,250
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec,Conditions=[['content-length-range',1,size_kb*1024]])
   return {"status":1,"message":output}

from boto3.s3.transfer import TransferConfig
@app.post("/private/s3-upload-file-multipart")
async def private_s3_upload_file_multipart(request:Request,bucket:str,key:str,file_path:str):
   s3_client.upload_file(file_path,bucket,key,Config=TransferConfig(multipart_threshold=8000000))
   return {"status":1,"message":"done"}

@app.get("/root/s3-download-url")
async def root_s3_download_url(request:Request,url:str,path:str):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   s3_client.download_file(bucket,key,path)
   return {"status":1,"message":"done"}

@app.delete("/root/s3-delete-url")
async def root_s3_delete_url(request:Request,url:str):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=s3_resource.Object(bucket,key).delete()
   return {"status":1,"message":output}

@app.get("/public/sns-otp-send")
async def public_sns_otp_send(request:Request,mobile:str,entity_id:str=None,sender_id:str=None,template_id:str=None,message:str=None):
   otp=random.randint(100000,999999)
   await postgres_client.execute(query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;",values={"otp":otp,"mobile":mobile})
   if not entity_id:output=sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   else:output=sns_client.publish(PhoneNumber=mobile,Message=message.replace("{otp}",str(otp)),MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return {"status":1,"message":output}

@app.get("/root/sns-check-opted-out")
async def root_sns_check_opted_out(request:Request,mobile:str):
   output=sns_client.check_if_phone_number_is_opted_out(phoneNumber=mobile)
   return {"status":1,"message":output}

@app.get("/root/sns-list-opted-mobile")
async def root_sns_list_opted_mobile(request:Request,next_token:str=None):
   output=sns_client.list_phone_numbers_opted_out(nextToken='' if not next_token else next_token)
   return {"status":1,"message":output}

@app.put("/root/sns-optin-mobile")
async def root_sns_optin_mobile(request:Request,mobile:str):
   output=sns_client.opt_in_phone_number(phoneNumber=mobile)
   return {"status":1,"message":output}

@app.get("/root/sns-list-sandbox-mobile")
async def root_sns_list_sandbox_mobile(request:Request,limit:int=100,next_token:str=None):
   if not next_token:output=sns_client.list_sms_sandbox_phone_numbers(MaxResults=limit)
   else:output=sns_client.list_sms_sandbox_phone_numbers(NextToken=next_token,MaxResults=limit)
   return {"status":1,"message":output}

@app.get("/public/ses-otp-send")
async def public_ses_otp_send(request:Request,sender:str,email:str):
   otp=random.randint(100000,999999)
   await postgres_client.fetch_all(query="insert into otp (otp,email) values (:otp,:email) returning *;",values={"otp":otp,"email":email})
   to,title,body=[email],"otp from atom",str(otp)
   ses_client.send_email(Source=sender,Destination={"ToAddresses":to},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return {"status":1,"message":"done"}

@app.get("/root/ses-list-identity")
async def root_ses_list_identity(request:Request,type:Literal["EmailAddress","Domain"],limit:int,next_token:str=None):
   output=ses_client.list_identities(IdentityType=type,NextToken='' if not next_token else next_token,MaxItems=limit)
   return {"status":1,"message":output}

@app.post("/root/ses-add-identity")
async def root_ses_add_identity(request:Request,type:Literal["email","domain"],identity:str):
   if type=="email":output=ses_client.verify_email_identity(EmailAddress=identity)
   if type=="domain":output=ses_client.verify_domain_identity(Domain=identity)
   return {"status":1,"message":output}

@app.get("/root/ses-identity-status")
async def root_ses_identity_status(request:Request,identity:str):
   output=ses_client.get_identity_verification_attributes(Identities=[identity])
   return {"status":1,"message":output}

@app.delete("/root/ses-delete-identity")
async def root_ses_delete_identity(request:Request,identity:str):
   output=ses_client.delete_identity(Identity=identity)
   return {"status":1,"message":output}

@app.delete("/root/redis-flush")
async def root_redis_flush(request:Request):
   output=await redis_client.flushall()
   return {"status":1,"message":output}

@app.post("/root/redis-set-object")
async def root_redis_set_object(request:Request,key:str,expiry:int=None):
   object=await request.json()
   object=json.dumps(object)
   if expiry:output=await redis_client.setex(key,expiry,object)
   else:output=await redis_client.set(key,object)
   return {"status":1,"message":output}

@app.get("/public/redis-get-object")
async def public_redis_get_object(request:Request,key:str):
   output=await redis_client.get(key)
   if output:output=json.loads(output)
   return {"status":1,"message":output}

@app.post("/root/redis-csv-set")
async def root_redis_csv_set(request:Request,table:str,file:UploadFile,expiry:int=None):
   file_csv=csv.DictReader(codecs.iterdecode(file.file,'utf-8'))
   object_list=[]
   for row in file_csv:object_list.append(row)
   file.file.close()
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if expiry:pipe.setex(key,expiry,json.dumps(object))
         else:pipe.set(key,json.dumps(object))
      await pipe.execute()
   return {"status":1,"message":"done"}

@app.post("/root/mongodb-create")
async def root_mongodb_create(request:Request,database:str,collection:str):
   database=mongodb_client[database]
   collection=database[collection]
   object=await request.json()
   output=await collection.insert_many([object])
   return {"status":1,"message":str(output)}

@app.get("/root/mongodb-read")
async def root_mongodb_read(request:Request,database:str,collection:str,_id:str):
   database=mongodb_client[database]
   collection=database[collection]
   _id=ObjectId(_id)
   output=await collection.find_one({"_id":_id})
   return {"status":1,"message":str(output)}

@app.put("/root/mongodb-update")
async def root_mongodb_update(request:Request,database:str,collection:str,_id:str):
   database=mongodb_client[database]
   collection=database[collection]
   _id=ObjectId(_id)
   object=await request.json()
   output=await collection.update_one({"_id":_id},{"$set":object})
   return {"status":1,"message":str(output)}

@app.delete("/root/mongodb-delete")
async def root_mongodb_delete(request:Request,database:str,collection:str,_id:str):
   database=mongodb_client[database]
   collection=database[collection]
   _id=ObjectId(_id)
   output=await collection.delete_one({"_id":_id})
   return {"status":1,"message":str(output)}

###main
import sys
mode=sys.argv
import asyncio,json

import asyncio,uvicorn
async def main_fastapi():
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info",reload=True)
   server=uvicorn.Server(config)
   await server.serve()
if __name__=="__main__" and len(mode)==1:
   try:asyncio.run(main_fastapi())
   except KeyboardInterrupt:print("exit")

import nest_asyncio
nest_asyncio.apply()

async def main_redis():
   #postgres client
   global postgres_client
   postgres_client=Database(postgres_database_url,min_size=1,max_size=100)
   await postgres_client.connect()
   

   
   global postgres_schema,postgres_column_datatype
   
   
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   await set_redis_client()
   try:
      async for message in redis_pubsub.listen():
         if message["type"]=="message" and message["channel"]==b'postgres_cud':
            data=json.loads(message['data'])
            await queue_pull(data,postgres_cud,postgres_client,object_serialize,postgres_column_datatype)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await redis_pubsub.unsubscribe("postgres_cud")
      await redis_client.aclose()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="redis":
    try:asyncio.run(main_redis())
    except KeyboardInterrupt:print("exit")

async def main_kafka():
   #postgres client
   global postgres_client
   postgres_client=Database(postgres_database_url,min_size=1,max_size=100)
   await postgres_client.connect()

   
   global postgres_schema,postgres_column_datatype
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   await set_kafka_client()
   try:
      async for message in kafka_consumer_client:
         if message.topic=="postgres_cud":
            data=json.loads(message.value.decode('utf-8'))
            await queue_pull(data,postgres_cud,postgres_client,object_serialize,postgres_column_datatype)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await kafka_consumer_client.stop()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="kafka":
    try:asyncio.run(main_kafka())
    except KeyboardInterrupt:print("exit")

def aqmp_callback(ch,method,properties,body):
   data=json.loads(body)
   loop=asyncio.get_event_loop()
   loop.run_until_complete(queue_pull(data,postgres_cud,postgres_client,object_serialize,postgres_column_datatype))
   return None

async def main_rabbitmq():
   #postgres client
   global postgres_client
   postgres_client=Database(postgres_database_url,min_size=1,max_size=100)
   await postgres_client.connect()

   
   global postgres_schema,postgres_column_datatype
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   await set_rabbitmq_client()
   try:
      rabbitmq_channel.basic_consume("postgres_cud",aqmp_callback,auto_ack=True)
      rabbitmq_channel.start_consuming()
   except KeyboardInterrupt:
      await postgres_client.disconnect()
      rabbitmq_channel.close()
      rabbitmq_client.close()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="rabbitmq":
    try:asyncio.run(main_rabbitmq())
    except KeyboardInterrupt:print("exit")

async def main_lavinmq():
   #postgres client
   global postgres_client
   postgres_client=Database(postgres_database_url,min_size=1,max_size=100)
   await postgres_client.connect()

   global postgres_schema,postgres_column_datatype
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   await set_lavinmq_client()
   try:
      lavinmq_channel.basic_consume("postgres_cud",aqmp_callback,auto_ack=True)
      lavinmq_channel.start_consuming()
   except KeyboardInterrupt:
      await postgres_client.disconnect()
      lavinmq_channel.close()
      lavinmq_client.close()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="lavinmq":
    try:asyncio.run(main_lavinmq())
    except KeyboardInterrupt:print("exit")
   