#env
import os
from dotenv import load_dotenv
load_dotenv()

#function
async def add_action_count(postgres_client,action,object_table,object_list):
   if not object_list:return {"status":1,"message":object_list}
   key_name=f"{action}_count"
   object_list=[dict(item)|{key_name:0} for item in object_list]
   parent_ids_list=[str(item["id"]) for item in object_list if item["id"]]
   parent_ids_string=",".join(parent_ids_list)
   if parent_ids_string:
      query=f"select parent_id,count(*) from {action} where parent_table=:parent_table and parent_id in ({parent_ids_string}) group by parent_id;"
      query_param={"parent_table":object_table}
      object_list_action=await postgres_client.fetch_all(query=query,values=query_param)
      for x in object_list:
         for y in object_list_action:
               if x["id"]==y["parent_id"]:
                  x[key_name]=y["count"]
                  break
   return {"status":1,"message":object_list}

async def add_creator_data(postgres_client,object_list):
   if not object_list:return {"status":1,"message":object_list}
   object_list=[dict(item)|{"created_by_username":None} for item in object_list]
   created_by_ids_list=[str(item["created_by_id"]) for item in object_list if item["created_by_id"]]
   created_by_ids_string=",".join(created_by_ids_list)
   if created_by_ids_string:
      query=f"select * from users where id in ({created_by_ids_string});"
      object_list_user=await postgres_client.fetch_all(query=query,values={})
      for x in object_list:
         for y in object_list_user:
            if x["created_by_id"]==y["id"]:
               x["created_by_username"]=y["username"]
               break
   return {"status":1,"message":object_list}

async def postgres_cud(postgres_client,postgres_schema,postgres_column_datatype,object_serialize,mode,table,object_list,is_serialize):
   missing_key=[key for key in object_list[0] if key not in postgres_schema[table].keys()]
   if missing_key:return {"status":0,"message":f"{missing_key} not in {table}"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   if mode=="create":
      column_insert_list=[*object_list[0]]
      query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   if mode=="update":
      column_update_list=[*object_list[0]]
      column_update_list.remove("id")
      query=f"update {table} set {','.join([f'{item}=coalesce(:{item},{item})' for item in column_update_list])} where id=:id returning *;"
   if mode=="delete":
      query=f"delete from {table} where id=:id;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      try:
         transaction=await postgres_client.transaction()
         output=await postgres_client.execute_many(query=query,values=object_list)
      except Exception as e:
         await transaction.rollback()
         print(e.args)
         return {"status":0,"message":e.args}
      else:
         await transaction.commit()
         output="done"
   return {"status":1,"message":output}

import hashlib,datetime,json
async def postgres_object_serialize(postgres_column_datatype,object_list):
   for index,object in enumerate(object_list):
      for k,v in object.items():
         datatype=postgres_column_datatype.get(k,None)
         if not datatype:return {"status":0,"message":f"column {k} is not in postgres schema"}
         if not v:object_list[index][k]=None
         if k in ["password","google_id"]:object_list[index][k]=hashlib.sha256(v.encode()).hexdigest() if v else None
         if "int" in datatype:object_list[index][k]=int(v) if v else None
         if datatype in ["numeric"]:object_list[index][k]=round(float(v),3) if v else None
         if "time" in datatype:object_list[index][k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
         if datatype in ["date"]:object_list[index][k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
         if datatype in ["jsonb"]:object_list[index][k]=json.dumps(v) if v else None
         if datatype in ["ARRAY"]:object_list[index][k]=v.split(",") if v else None
   return {"status":1,"message":object_list}

async def postgres_schema_init(postgres_client,config):
   postgres_schema={}
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   index_name_list=[object["indexname"] for object in (await postgres_client.fetch_all(query="select indexname from pg_indexes where schemaname='public';",values={}))]
   constraint_name_list=[object["constraint_name"] for object in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))]
   for query in config["query"]["extension"].split("---"):await postgres_client.fetch_all(query=query,values={})
   for table,v in config["table"].items():
      if table not in postgres_schema:await postgres_client.execute(f"create table if not exists {table} (id bigint primary key generated always as identity not null);", values={})
      for column in v:
         column=column.split("-")
         if not postgres_schema.get(table,{}).get(column[0],None):await postgres_client.execute(f"alter table {table} add column if not exists {column[0]} {column[1]};", values={})
         [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
         if column[2]=="1" and postgres_schema.get(table,{}).get(column[0],{}).get("nullable")=="YES":await postgres_client.execute(f"alter table {table} alter column {column[0]} set not null;", values={})
         if column[3]!="0" and f"index_{table}_{column[0]}" not in index_name_list:await postgres_client.execute(query=f"create index concurrently if not exists index_{table}_{column[0]} on {table} using {column[3]} ({column[0]});",values={})
   for k,v in config["query"].items():
      for query in v.split("---"):
         if "add constraint" in query and query.split()[5] in constraint_name_list:continue
         await postgres_client.fetch_all(query=query,values={})
   return {"status":1,"message":"done"}

#globals
postgres_database_url=os.getenv("postgres_database_url")
redis_server_url=os.getenv("redis_server_url")
key_root=os.getenv("key_root")
key_jwt=os.getenv("key_jwt")
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
users_type_ids={}
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
"project":["type-text-1-btree","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0"],
"users":["created_at-timestamptz-0-brin","created_by_id-bigint-0-btree","updated_at-timestamptz-0-0","updated_by_id-bigint-0-0","is_active-smallint-0-btree","is_protected-smallint-0-btree","type-text-0-btree","username-text-0-0","password-text-0-btree","location-geography(POINT)-0-gist","metadata-jsonb-0-0","google_id-text-0-btree","last_active_at-timestamptz-0-0","date_of_birth-date-0-0","email-text-0-btree","mobile-text-0-btree","name-text-0-0"],
"post":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","updated_at-timestamptz-0-0","updated_by_id-bigint-0-0","type-text-0-0","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0","location-geography(POINT)-0-0","metadata-jsonb-0-0"],
"message":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","user_id-bigint-1-btree","description-text-0-0","is_read-smallint-0-btree"],
"helpdesk":["created_at-timestamptz-0-0","created_by_id-bigint-0-0","status-text-0-0","remark-text-0-0","type-text-0-0","description-text-1-0"],
"otp":["created_at-timestamptz-0-0","otp-integer-1-0","email-text-0-btree","mobile-text-0-btree"],
"log_api":["created_at-timestamptz-0-0","created_by_id-bigint-0-0","api-text-0-0","status_code-smallint-0-0","response_time_ms-numeric(1000,3)-0-0"],
"log_password":["created_at-timestamptz-0-0","user_id-bigint-0-0","password-text-0-0"],
"action_like":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_bookmark":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_report":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_block":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_follow":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_rating":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","rating-numeric(10,3)-0-0"],
"action_comment":["created_at-timestamptz-0-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","description-text-0-0"],
"human":["created_at-timestamptz-0-0","name-text-0-0"],
},
"query":{
"default_created_at":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'created_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"default_updated_at":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';---DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'updated_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'is_protected' AND table_schema = 'public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected = 1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"extension":"create extension if not exists postgis",
"delete_disable_bulk":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;---create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"log_password":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;---CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"root_user":"insert into users (username,password) values ('atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3') on conflict do nothing;---create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"unique":"alter table users add constraint constraint_unique_users_username unique (username);---alter table action_like add constraint constraint_unique_action_like_cpp unique (created_by_id,parent_table,parent_id);---alter table action_bookmark add constraint constraint_unique_action_bookmark_cpp unique (created_by_id,parent_table,parent_id);---alter table action_report add constraint constraint_unique_action_report_cpp unique (created_by_id,parent_table,parent_id);---alter table action_block add constraint constraint_unique_action_block_cpp unique (created_by_id,parent_table,parent_id);---alter table action_follow add constraint constraint_unique_action_follow_cpp unique (created_by_id,parent_table,parent_id);",
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

async def set_users_type_ids():
   global users_type_ids
   users_type_ids["admin"]=[]
   if postgres_schema.get("users",{}).get("type",{}):
      users_type_ids["admin"].extend(object["id"] for object in (await postgres_client.fetch_all(query="select id from users where type='admin' limit 1000000", values={})))
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
import jwt,json
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param=str(dict(sorted(request.query_params.items())))
   token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
   user_id=0
   if token:user_id=json.loads(jwt.decode(token,os.getenv("key_jwt"),algorithms="HS256")["data"])["id"]
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
   await set_users_type_ids()
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
   try:
      #token
      user={}
      token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
      if token:user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
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
         end=time.time()
         status_code=response.status_code
         response_time_ms=(end-start)*1000
         #api log
         if "log_api" in postgres_schema:
            global object_list_log
            object={"created_by_id":user.get("id",None),"api":api,"status_code":status_code,"response_time_ms":response_time_ms}
            object_list_log.append(object)
            if len(object_list_log)>=3:
               response.background=BackgroundTask(postgres_cud,postgres_client,postgres_schema,postgres_column_datatype,postgres_object_serialize,"create","log_api",object_list_log,0)
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

@app.post("/schema-init")
async def schema_init(request:Request,mode:str,key:str):
   if key!=key_root:return {"status":0,"message":"key issue"}
   if mode=="default":config=postgres_config_default
   if mode=="self":config=await request.json()
   await postgres_schema_init(postgres_client,config)
   return {"status":1,"message":"done"}

@app.get("/clean")
async def clean():
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
   await postgres_client.execute(query="truncate table log_api;",values={})
   #final
   return {"status":1,"message":"done"}

@app.get("/query-runner")
async def query_runner(query:str):
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

@app.get("/reset-global")
async def reset_global():
   await set_postgres_schema()
   await set_project_data()
   await set_users_type_ids()
   return {"status":1,"message":"done"}

@app.get("/signup",dependencies=[Depends(RateLimiter(times=1,seconds=3))])
async def signup(username:str,password:str):
   query="insert into users (username,password) values (:username,:password) returning *;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.get("/login")
async def login(request:Request):
   query_param=dict(request.query_params)
   mode,username,password,google_id,email,mobile,otp=query_param.get("mode",None),query_param.get("username",None),query_param.get("password",None),query_param.get("google_id",None),query_param.get("email",None),query_param.get("mobile",None),query_param.get("otp",None)
   #otp verify
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
      if not email or not otp:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wromg param"})
      output=await postgres_client.fetch_all(query="select id from users where email=:email order by id desc limit 1;",values={"email":email})
      if not output:output=await postgres_client.fetch_all(query="insert into users (email) values (:email) returning *;",values={"email":email})
      user=output[0] if output else None
   if mode=="mo":
      if not mobile or not otp:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wromg param"})
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
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   #final
   return {"status":1,"message":token}

@app.get("/profile")
async def profile(request:Request,background:BackgroundTasks):
   if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token issue"})
   output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   user=output[0] if output else None
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   background.add_task(postgres_client.execute,query="update users set last_active_at=:last_active_at where id=:id",values={"id":request.state.user["id"],"last_active_at":datetime.datetime.now()})
   return {"status":1,"message":user}

@app.get("/token-refresh")
async def token_refresh(request:Request):
   if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token issue"})
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":request.state.user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/delete-account")
async def delete_account(request:Request):
   if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
   output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   user=output[0] if output else None
   if user["type"]=="admin":return responses.JSONResponse(status_code=200,content={"status":0,"message":"admin cant be deleted"})
   output=await postgres_client.execute(query="delete from users where id=:id;",values={"id":request.state.user["id"]})
   return {"status":1,"message":output}

@app.post("/object-create")
async def object_create(request:Request,mode:Literal["public","self","admin"],table:str,queue:str=None):
   #object
   object=await request.json()
   if request.state.user and postgres_schema.get(table,{}).get("created_by_id",None):object["created_by_id"]=request.state.user["id"]
   #auth
   if table not in ["post","helpdesk","human","project","atom","message","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if mode=="public":
      if table not in ["helpdesk","human"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
      if any(k in ["id","created_at","updated_at","updated_by_id","is_active","is_verified","is_deleted","password","google_id","otp"] for k in object):return responses.JSONResponse(status_code=400, content={"status":0,"message":"key denied"})
   if mode=="self":
      if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
      if table not in ["post","helpdesk","human","message","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
      if any(k in ["id","created_at","updated_at","updated_by_id","is_active","is_verified","is_deleted","password","google_id","otp"] for k in object):return responses.JSONResponse(status_code=400, content={"status":0,"message":"key denied"})
   if mode=="admin":
      if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
      if request.state.user["id"] not in users_type_ids["admin"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"only admin allowed"})
   #logic
   if not queue:
      response=await postgres_cud(postgres_client,postgres_schema,postgres_column_datatype,postgres_object_serialize,"create",table,[object],1)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      output=response["message"]
   #queue
   if queue:
      data={"mode":"create","table":table,"object":object}
      channel="postgres_cud"
      if queue=="redis":output=await redis_client.publish(channel,json.dumps(data))
      if queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=channel,body=json.dumps(data))
      if queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=channel,body=json.dumps(data))
      if queue=="kafka":output=await kafka_producer_client.send_and_wait(channel,json.dumps(data,indent=2).encode('utf-8'),partition=0)
   #final
   return {"status":1,"message":output}

@app.put("/object-update")
async def object_update(request:Request,mode:Literal["self","admin"],table:str,otp:int=None):
   #object
   object=await request.json()
   if request.state.user and postgres_schema.get(table,{}).get("updated_by_id",None):object["updated_by_id"]=request.state.user["id"]
   #auth
   if table not in ["users","post","helpdesk","human","project","atom","message","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if mode=="self":
      if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
      if table not in ["users","post","message","action_comment"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
      if any(k in ["created_at","created_by_id","is_active","is_verified","type","google_id","otp"] for k in object): return responses.JSONResponse(status_code=400, content={"status":0,"message":f"key denied"})
      if table=="users" and object["id"]!=request.state.user["id"]:return {"status":0,"message":"object ownership issue"}
      if table!="users" and (not (output := await postgres_client.fetch_all(query=f"select created_by_id from {table} where id=:id;", values={"id": object["id"]})) or output[0]["created_by_id"] != request.state.user["id"]): return {"status": 0, "message": "no object" if not output else "object ownership issue"}
   if mode=="admin":
      if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
      if request.state.user["id"] not in users_type_ids["admin"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"only admin allowed"})
   #otp verify
   email,mobile=object.get("email",None),object.get("mobile",None)
   if table=="users" and (email or mobile):
      if not otp:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp must"})
      if email:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;",values={"email":email})
      if mobile:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;",values={"mobile":mobile})
      if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
      if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #logic
   response=await postgres_cud(postgres_client,postgres_schema,postgres_column_datatype,postgres_object_serialize,"update",table,[object],1)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   output=response["message"]
   #final
   return {"status":1,"message":output}

@app.get("/delete-ids")
async def delete_ids(request:Request,mode:Literal["self","admin"],table:str,ids:str=None):
   if table not in ["post","helpdesk","human","project","atom","message","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
   if mode=="admin":await postgres_client.execute(query=f"delete from {table} where id in ({ids});",values={})
   if mode=="self":await postgres_client.execute(query=f"delete from {table} where id in ({ids}) and created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/object-read")
@cache(expire=60)
async def object_read(request:Request,mode:Literal["public","self","admin","location"],table:str,order:str="id desc",limit:int=100,page:int=1,is_creator_data:int=0,action_count:str=None,location_data:str=None):
   #object
   object=dict(request.query_params)
   #auth
   if mode=="public":
      query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   if mode=="self":
      if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
      object["created_by_id"]=f"=,{request.state.user['id']}"
      query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   if mode=="admin":
      if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token is must"})
      if request.state.user["id"] not in users_type_ids["admin"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"only admin allowed"})
      query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   if mode=="location":
      long,lat,min_meter,max_meter=float(location_data.split(",")[0]),float(location_data.split(",")[1]),int(location_data.split(",")[2]),int(location_data.split(",")[3])
      query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
   #where string
   object={k:v for k,v in object.items() if k in postgres_schema.get(table,{})}
   object_key_operator={k:v.split(',',1)[0] for k,v in object.items()}
   object_key_value={k:v.split(',',1)[1] for k,v in object.items()}
   column_read_list=[*object]
   where_column_single_list=[f"({column} {object_key_operator[column]} :{column} or :{column} is null)" for column in column_read_list]
   where_column_joined=' and '.join(where_column_single_list)
   where_string,where_value=f"where {where_column_joined}" if where_column_joined else "",object_key_value
   #serialize
   response=await postgres_object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #query run
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   #addons
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
   response=await postgres_object_serialize(postgres_column_datatype,[object])
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
   "users_type_ids":users_type_ids,
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
      response=await postgres_object_serialize(postgres_column_datatype,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud(postgres_client,"create",table,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response




@app.post("/admin/object-create")
async def admin_object_create(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   if postgres_schema[table].get("created_by_id",None):object["created_by_id"]=request.state.user["id"]
   #object serialize
   if is_serialize:
      response=await postgres_object_serialize(postgres_column_datatype,[object])
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud(postgres_client,"create",table,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   output=response["message"]
   #final
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def admin_object_update(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   if postgres_schema[table].get("updated_by_id",None):object["updated_by_id"]=request.state.user["id"]
   #serialize
   if is_serialize:
      response=await postgres_object_serialize(postgres_column_datatype,[object])
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
      response=await postgres_object_serialize(postgres_column_datatype,object_list)
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
            await queue_pull(data,postgres_cud,postgres_client,postgres_object_serialize,postgres_column_datatype)
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
            await queue_pull(data,postgres_cud,postgres_client,postgres_object_serialize,postgres_column_datatype)
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
   loop.run_until_complete(queue_pull(data,postgres_cud,postgres_client,postgres_object_serialize,postgres_column_datatype))
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
   