#env
import os
from dotenv import load_dotenv
load_dotenv()

#function
async def postgres_cud(mode,table,object_list,postgres_client):
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
         return {"status":0,"message":e.args}
      else:
         await transaction.commit()
         output="done"
   return {"status":1,"message":output}

async def postgres_object_where_parse(object_where,postgres_column_datatype):
   object_where={k:v for k,v in object_where.items() if k in postgres_column_datatype}
   object_where={k:v for k,v in object_where.items() if k not in ["location","metadata"]}
   object_where={k:v for k,v in object_where.items() if k not in ["table","order","limit","page"]}
   object_operator={k:v.split(',',1)[0] for k,v in object_where.items()}
   object_value={k:v.split(',',1)[1] for k,v in object_where.items()}
   column_read_list=[*object_where]
   where_column_single_list=[f"({column} {object_operator[column]} :{column} or :{column} is null)" for column in column_read_list]
   where_column_joined=' and '.join(where_column_single_list)
   where_string=f"where {where_column_joined}" if where_column_joined else ""
   where_value=object_value
   return {"status":1,"message":[where_string,where_value]}

import hashlib,datetime,json
async def postgres_serialize(object_list,postgres_column_datatype):
   for index,object in enumerate(object_list):
      for k,v in object.items():
         if k in postgres_column_datatype:datatype=postgres_column_datatype[k]
         else:return {"status":0,"message":f"{k} column not in postgres_column_datatype"}
         if not v:object_list[index][k]=None
         if k in ["password","google_id"]:object_list[index][k]=hashlib.sha256(v.encode()).hexdigest() if v else None
         if "int" in datatype:object_list[index][k]=int(v) if v else None
         if datatype in ["numeric"]:object_list[index][k]=round(float(v),3) if v else None
         if "time" in datatype:object_list[index][k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
         if datatype in ["date"]:object_list[index][k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
         if datatype in ["jsonb"]:object_list[index][k]=json.dumps(v) if v else None
         if datatype in ["ARRAY"]:object_list[index][k]=v.split(",") if v else None
   return {"status":1,"message":object_list}

async def postgres_add_action_count(action,table,object_list,postgres_client):
   if not object_list:return {"status":1,"message":object_list}
   key_name=f"{action}_count"
   object_list=[dict(item)|{key_name:0} for item in object_list]
   parent_ids_list=[str(item["id"]) for item in object_list if item["id"]]
   parent_ids_string=",".join(parent_ids_list)
   if parent_ids_string:
      query=f"select parent_id,count(*) from {action} where parent_table=:parent_table and parent_id in ({parent_ids_string}) group by parent_id;"
      query_param={"parent_table":table}
      object_list_action=await postgres_client.fetch_all(query=query,values=query_param)
      for x in object_list:
         for y in object_list_action:
               if x["id"]==y["parent_id"]:
                  x[key_name]=y["count"]
                  break
   return {"status":1,"message":object_list}

async def postgres_add_creator_data(object_list,postgres_client):
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

import uvicorn
async def fastapi_app_start(app):
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info",reload=True)
   server=uvicorn.Server(config)
   await server.serve()

import redis.asyncio as redis
import asyncio
import async_timeout
async def redis_subscriber_start(redis_server_url,channel):
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_server_url))
   redis_pubsub=redis_client.pubsub()
   await redis_pubsub.psubscribe(channel)
   while True:
      try:
         async with async_timeout.timeout(1):
               message=await redis_pubsub.get_message(ignore_subscribe_messages=True)
               if message is not None:
                  print(message)
                  if message["data"].decode()=="stop":break
      except asyncio.TimeoutError:pass

from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def kafka_consumer_start(server_url,path_cafile,path_certfile,path_keyfile,topic):
   context=create_ssl_context(cafile=path_cafile,certfile=path_certfile,keyfile=path_keyfile)
   consumer=AIOKafkaConsumer(topic,bootstrap_servers=server_url,security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
   await consumer.start()
   try:
      async for msg in consumer:
         print("consumed:",msg.topic, msg.partition, msg.offset,msg.key, msg.value, msg.timestamp)
   finally:
      await consumer.stop()
      
def lavinmq_consumer_logic(ch,method,properties,body):
   print(body)
   return None

def rabbitmq_consumer_logic(ch,method,properties,body):
   print(body)
   return None
   
#sentry
import sentry_sdk
sentry_dsn=os.getenv("sentry_dsn")
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

#redis key builder(impure function)
from fastapi import Request,Response
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param=str(dict(sorted(request.query_params.items())))
   user_id=0
   gate=api.split("/")[1]
   token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
   if gate=="my":user_id=json.loads(jwt.decode(token,os.getenv("secret_key_jwt"),algorithms="HS256")["data"])["id"]
   key=api+"---"+str(user_id)+"---"+query_param
   return key

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
from databases import Database
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
postgres_client=None
redis_client=None
postgres_column_datatype=None
@asynccontextmanager
async def lifespan(app:FastAPI):
   #postgres
   global postgres_client
   postgres_client=Database(os.getenv("postgres_database_url"),min_size=1,max_size=100)
   await postgres_client.connect()
   #redis
   global redis_client
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(os.getenv("redis_server_url")))
   await FastAPILimiter.init(redis_client)
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   #postgres column data type
   global postgres_column_datatype
   query_master='''
   with 
   t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),
   c as (select * from information_schema.columns where table_schema='public')
   select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name
   '''
   output=await postgres_client.fetch_all(query=query_master,values={})
   postgres_column_datatype={item["column_name"]:item["data_type"] for item in output}
   #disconnect
   yield
   await postgres_client.disconnect()
   await redis_client.aclose()
   
#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#middleware
from fastapi import Request,responses
from starlette.background import BackgroundTask
import time,jwt,json,traceback
object_list_log=[]
@app.middleware("http")
async def middleware(request:Request,api_function):
   try:
      #start
      start=time.time()
      token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
      api=request.url.path
      gate=api.split("/")[1]
      user=None
      method=request.method
      #auth check
      if gate not in ["","docs","openapi.json","root","auth","my","public","private","admin"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"gate not allowed"})
      if gate=="root" and token!=os.getenv("secret_key_root"):return responses.JSONResponse(status_code=400,content={"status":0,"message":"token root mismatch"})
      if gate in ["my","private","admin"]:user=json.loads(jwt.decode(token,os.getenv("secret_key_jwt"),algorithms="HS256")["data"])
      if gate in ["admin"]:
         output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":user["id"]})
         user=output[0] if output else None
         if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
      if gate in ["admin"]:
         if not user["api_access"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"user not admin"})
         if api not in user["api_access"].split(","):return responses.JSONResponse(status_code=400,content={"status":0,"message":"api access denied"})
      #request state assign
      request.state.user=user
      #api response
      response=await api_function(request)
      #end
      end=time.time()
      response_time_ms=(end-start)*1000
      #log_api create
      global object_list_log
      object={"created_by_id":user["id"] if user else None,"api":api,"status_code":response.status_code,"response_time_ms":response_time_ms}
      object_list_log.append(object)
      if len(object_list_log)>=3:
         query="insert into log_api (created_by_id,api,status_code,response_time_ms) values (:created_by_id,:api,:status_code,:response_time_ms)"
         query_param=object_list_log
         BackgroundTask(await postgres_client.execute_many(query=query,values=query_param))
         object_list_log=[]
   except Exception as e:
      print(traceback.format_exc())
      return responses.JSONResponse(status_code=400,content={"status":0,"message":e.args})
   return response

#router
import os,glob
current_directory_path=os.path.dirname(os.path.realpath(__file__))
file_path_list=glob.glob(f"{current_directory_path}/*")
file_name_list=[item.rsplit("/",1)[-1] for item in file_path_list]
file_name_list_without_extension=[item.split(".")[0] for item in file_name_list]
for item in file_name_list_without_extension:
   if "api" in item:
      router=__import__(item).router
      app.include_router(router)

#api
from fastapi import Request,UploadFile,responses,BackgroundTasks,Depends
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter
import hashlib,datetime,json,uuid,time,jwt,csv,codecs,copy

@app.get("/")
async def root(request:Request):
   return {"status":1,"message":"welcome to atom"}

#root/postgres-schema-init
@app.post("/root/postgres-schema-init")
async def root_postgres_schema_init(request:Request,mode:str):
   #schema define
   if mode=="self":schema=await request.json()
   if mode=="default":schema={
   "extension":["postgis"],
   "table":["atom","human","users","post","message","helpdesk","otp","action_like","action_bookmark","action_report","action_block","action_rating","action_comment","action_follow","log_api","log_password"],
   "column":{
   "created_at":["timestamptz",["atom","human","users","post","message","helpdesk","otp","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment","log_api","log_password"]],
   "created_by_id":["bigint",["atom","human","users","post","message","helpdesk","otp","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment","log_api","log_password"]],
   "updated_at":["timestamptz",["atom","human","users","post","message","helpdesk","action_report","action_comment"]],
   "updated_by_id":["bigint",["atom","human","users","post","message","helpdesk","action_report","action_comment"]],
   "is_active":["smallint",["users","post","action_comment"]],
   "is_verified":["smallint",["users","post","action_comment"]],
   "is_protected":["smallint",["users","post"]],
   "is_read":["smallint",["message"]],
   "is_deleted":["smallint",[]],
   "otp":["integer",["otp"]],
   "user_id":["bigint",["message","log_password"]],
   "parent_table":["text",["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]],
   "parent_id":["bigint",["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]],
   "location":["geography(POINT)",["users","post","atom"]],
   "api":["text",["log_api"]],
   "status_code":["smallint",["log_api"]],
   "response_time_ms":["numeric",["log_api"]],
   "type":["text",["atom","users","post","helpdesk"]],
   "status":["text",["action_report","helpdesk"]],
   "remark":["text",["action_report","helpdesk"]],
   "rating":["numeric",["post","action_rating"]],
   "metadata":["jsonb",["users","post"]],
   "username":["text",["users"]],
   "password":["text",["users","log_password"]],
   "google_id":["text",["users"]],
   "profile_pic_url":["text",["users"]],
   "last_active_at":["timestamptz",["users"]],
   "api_access":["text",["users"]],
   "name":["text",["users","human"]],
   "email":["text",["users","post","otp","helpdesk","human"]],
   "mobile":["text",["users","post","otp","helpdesk","human"]],
   "country":["text",["users","human"]],
   "state":["text",["users","human"]],
   "city":["text",["users"]],
   "date_of_birth":["date",["users","human"]],
   "interest":["text",["users","human"]],
   "skill":["text",["users","human"]],
   "gender":["text",["users","human"]],
   "title":["text",["atom","users","post"]],
   "description":["text",["atom","users","post","action_comment","message","helpdesk"]],
   "file_url":["text",["atom","post"]],
   "link_url":["text",["atom","post"]],
   "tag":["text",["atom","users","post"]],
   "tag_array":["text[]",[]],
   "number":["numeric",["atom"]],
   },
   "index":{
   "created_at":["brin",["users","post"]],
   "created_by_id":["btree",["users","post","message","helpdesk","otp","action_rating","action_comment","log_api"]],
   "is_active":["btree",["users","post","action_comment"]],
   "is_verified":["btree",["users","post","action_comment"]],
   "is_read":["btree",["message"]],
   "user_id":["btree",["message"]],
   "parent_table":["btree",["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]],
   "parent_id":["btree",["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]],
   "type":["btree",["atom","users","post","helpdesk"]],
   "status":["btree",["action_report","helpdesk"]],
   "email":["btree",["users","otp"]],
   "mobile":["btree",["users","otp"]],
   "password":["btree",["users"]],
   "location":["gist",["users","post"]],
   "tag":["btree",["atom","users","post"]],
   "rating":["btree",["action_rating","post"]],
   "tag_array":["gin",[]]
   },
   "not_null":{"created_by_id":["message"],"user_id":["message"],"parent_table":["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"],"parent_id":["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]},
   "unique":{"username":["users"],"created_by_id,parent_table,parent_id":["action_like","action_bookmark","action_report","action_block","action_follow"]},
   "bulk_delete_disable":{"users":1},
   "query":{}
   }
   #extension (config)
   for item in schema["extension"]:
      query=f"create extension if not exists {item}"
      await postgres_client.fetch_all(query=query,values={})
   #table (config)
   output=await postgres_client.fetch_all(query="select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE';",values={})
   table_name_list=[item["table_name"] for item in output]
   for item in schema["table"]:
      if item not in table_name_list:
         query=f"create table if not exists {item} (id bigint primary key generated always as identity not null);"
         await postgres_client.fetch_all(query=query,values={})
   #column (config)
   query_master='''
   with 
   t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),
   c as (select * from information_schema.columns where table_schema='public')
   select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name
   '''
   output=await postgres_client.fetch_all(query=query_master,values={})
   table_column_list=[f"{item['table_name']}_{item['column_name']}" for item in output]
   for k,v in schema["column"].items():
      for item in v[1]:
         if f"{item}_{k}" not in table_column_list:
            query=f"alter table {item} add column if not exists {k} {v[0]};"
            await postgres_client.fetch_all(query=query,values={})
   #index (config)
   output=await postgres_client.fetch_all(query="select indexname from pg_indexes where schemaname='public';",values={})
   index_name_list=[item["indexname"] for item in output]
   for k,v in schema["index"].items():
      for item in v[1]:
         index_name=f"index_{item}_{k}"
         if index_name not in index_name_list:
            query=f"create index concurrently if not exists {index_name} on {item} using {v[0]} ({k});"
            await postgres_client.fetch_all(query=query,values={}) 
   #notnull (config)
   query_master='''
   with 
   t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),
   c as (select * from information_schema.columns where table_schema='public')
   select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name
   '''
   output=await postgres_client.fetch_all(query=query_master,values={})
   table_column_nullable_mapping={f"{item['table_name']}_{item['column_name']}":item["is_nullable"] for item in output}
   for k,v in schema["not_null"].items():
      for item in v:
         if table_column_nullable_mapping[f"{item}_{k}"]=="YES":
            query=f"alter table {item} alter column {k} set not null;"
            await postgres_client.fetch_all(query=query,values={})
   #unique (config)
   output=await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={})
   constraint_name_list=[item["constraint_name"] for item in output]
   for k,v in schema["unique"].items():
      for item in v:
         if len(k.split(","))==1:constraint_name=f"constraint_unique_{item}_{k}"
         else:constraint_name=f"constraint_unique_{item}_{"".join([item[0] for item in k.split(',')])}"
         if constraint_name not in constraint_name_list:
            query=f"alter table {item} add constraint {constraint_name} unique ({k});"
            await postgres_client.fetch_all(query=query,values={})
   #bulk delete disable (config)
   function_delete_disable_bulk="create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;"
   await postgres_client.fetch_all(query=function_delete_disable_bulk,values={})
   for k,v in schema["bulk_delete_disable"].items():
      trigger_name=f"trigger_delete_disable_bulk_{k}"
      query=f"create or replace trigger {trigger_name} after delete on {k} referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk({v});"
      await postgres_client.fetch_all(query=query,values={})
   #query (config)
   output=await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={})
   constraint_name_list=[item["constraint_name"] for item in output]
   for k,v in schema["query"].items():
      if "add constraint" in v and v.split()[5] in constraint_name_list:continue
      await postgres_client.fetch_all(query=v,values={})
   #set created_at default (auto)
   query_master='''
   with 
   t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),
   c as (select * from information_schema.columns where table_schema='public')
   select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name
   '''
   output=await postgres_client.fetch_all(query=query_master,values={})
   for item in output:
      if item["column_name"]=="created_at" and not item["column_default"]:
         query=f"alter table only {item['table_name']} alter column created_at set default now();"
         await postgres_client.fetch_all(query=query,values={})
   #set updated at now (auto)
   await postgres_client.fetch_all(query="create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';",values={})
   output=await postgres_client.fetch_all(query="select trigger_name from information_schema.triggers;",values={})
   trigger_name_list=[item["trigger_name"] for item in output]
   query_master='''
   with 
   t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),
   c as (select * from information_schema.columns where table_schema='public')
   select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name
   '''
   output=await postgres_client.fetch_all(query=query_master,values={})
   for item in output:
      if item["column_name"]=="updated_at":
         trigger_name=f"trigger_set_updated_at_now_{item['table_name']}"
         if trigger_name not in trigger_name_list:
            query=f"create or replace trigger {trigger_name} before update on {item['table_name']} for each row execute procedure function_set_updated_at_now();"
            await postgres_client.fetch_all(query=query,values={})
   #create rule protection (auto)
   output=await postgres_client.fetch_all(query="select rulename from pg_rules;",values={})
   rule_name_list=[item["rulename"] for item in output]
   query_master='''
   with 
   t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),
   c as (select * from information_schema.columns where table_schema='public')
   select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name
   '''
   output=await postgres_client.fetch_all(query=query_master,values={})
   for item in output:
      if item["column_name"]=="is_protected":
         rule_name=f"rule_protect_{item['table_name']}"
         if rule_name not in rule_name_list:
            query=f"create or replace rule {rule_name} as on delete to {item['table_name']} where old.is_protected=1 do instead nothing;"
            await postgres_client.fetch_all(query=query,values={})
   #root user (auto)
   await postgres_client.fetch_all(query="insert into users (username,password) values ('atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3') on conflict do nothing;",values={})
   await postgres_client.fetch_all(query=  "create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",values={})
   #refresh mat all (auto)
   query='''
   DO
   $$ DECLARE r RECORD; 
   BEGIN FOR r IN 
   (select oid::regclass::text as mat_name from pg_class where relkind='m') 
   LOOP
   EXECUTE 'refresh materialized view ' || quote_ident(r.mat_name); 
   END LOOP;
   END $$;
   '''
   await postgres_client.fetch_all(query=query,values={})
   #log password change (auto)
   function_log_password_change='''
   CREATE OR REPLACE FUNCTION function_log_password_change() 
   RETURNS TRIGGER LANGUAGE PLPGSQL 
   AS $$ 
   BEGIN 
   IF OLD.password <> NEW.password 
   THEN 
   INSERT INTO log_password(created_by_id,user_id,password) VALUES(NEW.updated_by_id,OLD.id,OLD.password); 
   END IF; 
   RETURN NEW; 
   END; 
   $$;
   '''
   await postgres_client.fetch_all(query=function_log_password_change,values={})
   trigger_log_password_change='''
   CREATE OR REPLACE TRIGGER trigger_log_password_change 
   AFTER UPDATE ON users 
   FOR EACH ROW 
   WHEN (OLD.password IS DISTINCT FROM NEW.password) 
   EXECUTE FUNCTION function_log_password_change();
   '''
   await postgres_client.fetch_all(query=trigger_log_password_change,values={})
   #procedure delete user (auto)
   query='''
   create or replace procedure procedure_delete_user(a int)
   language plpgsql
   as $$
   begin 
   delete from users where id=a;
   delete from post where created_by_id=a;
   delete from message where created_by_id=a;
   delete from message where user_id=a;
   delete from action_like where created_by_id=a;
   delete from action_bookmark where created_by_id=a;
   delete from action_report where created_by_id=a;
   delete from action_block where created_by_id=a;
   delete from action_follow where created_by_id=a;
   delete from action_rating where created_by_id=a;
   delete from action_comment where created_by_id=a;
   commit;
   end;
   $$;
   '''
   await postgres_client.fetch_all(query=query,values={})
   #final
   return {"status":1,"message":"done"}

#root/postgres-query-runner
@app.get("/root/postgres-query-runner")
async def root_postgres_query_runner(request:Request,query:str):
   query_list=query.split("---")
   if len(query_list)==1:output=await postgres_client.fetch_all(query=query,values={})
   else:
      transaction=await postgres_client.transaction()
      try:[await postgres_client.fetch_all(query=item,values={}) for item in query_list]
      except Exception as e:
         await transaction.rollback()
         return responses.JSONResponse(status_code=400,content={"status":0,"message":e.args})
      else:
         await transaction.commit()
         output="done"
   return {"status":1,"message":output}
      
#root/grant all api access
@app.put("/root/grant-all-api-access")
async def root_grant_all_api_access(request:Request,user_id:int):
   #api list
   api_list=[route.path for route in request.app.routes]
   api_list_admin=[item for item in api_list if "/admin" in item]
   api_list_admin_str=",".join(api_list_admin)
   #logic
   query="update users set api_access=:api_access where id=:id returning *"
   query_param={"api_access":api_list_admin_str,"id":user_id}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#auth/signup
@app.post("/auth/signup",dependencies=[Depends(RateLimiter(times=1,seconds=1))])
async def auth_signup(request:Request,username:str,password:str):
   #create user
   query="insert into users (username,password) values (:username,:password) returning *;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=user=output[0]
   #create token
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#auth/login
@app.get("/auth/login")
async def auth_login(request:Request,username:str,password:str,mode:str=None):
   #read user
   query=f"select * from users where username=:username and password=:password order by id desc limit 1;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   #check user
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   if mode=="admin" and not user["api_access"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no admin"})
   #create token
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#auth/login-google
@app.get("/auth/login-google")
async def auth_login_google(request:Request,google_id:str):
   #read user
   query=f"select * from users where google_id=:google_id order by id desc limit 1;"
   query_param={"google_id":hashlib.sha256(google_id.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   #create user
   if not user:
     query=f"insert into users (google_id) values (:google_id) returning *;"
     query_param={"google_id":hashlib.sha256(google_id.encode()).hexdigest()}
     output=await postgres_client.fetch_all(query=query,values=query_param)
     user_id=output[0]["id"]
     query="select * from users where id=:id;"
     query_param={"id":user_id}
     output=await postgres_client.fetch_all(query=query,values=query_param)
     user=output[0]
   #create token
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#auth/login-email-otp
@app.get("/auth/login-email-otp")
async def auth_login_email_otp(request:Request,email:str,otp:int,mode:str=None):
   #verify otp
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
   query_param={"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #read user
   query=f"select * from users where email=:email order by id desc limit 1;"
   query_param={"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   if mode=="exist" and not user:return responses.JSONResponse(status_code=400,content={"status":1,"message":"no user"})
   #create user
   if not user:
     query=f"insert into users (email) values (:email) returning *;"
     query_param={"email":email}
     output=await postgres_client.fetch_all(query=query,values=query_param)
     user_id=output[0]["id"]
     query="select * from users where id=:id;"
     query_param={"id":user_id}
     output=await postgres_client.fetch_all(query=query,values=query_param)
     user=output[0]
   #create token
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#auth/login-mobile-otp
@app.get("/auth/login-mobile-otp")
async def auth_login_mobile_otp(request:Request,mobile:str,otp:int,mode:str=None):
   #verify otp
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
   query_param={"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #read user
   query=f"select * from users where mobile=:mobile order by id desc limit 1;"
   query_param={"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   if mode=="exist" and not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create user
   if not user:
     query=f"insert into users (mobile) values (:mobile) returning *;"
     query_param={"mobile":mobile}
     output=await postgres_client.fetch_all(query=query,values=query_param)
     user_id=output[0]["id"]
     query="select * from users where id=:id;"
     query_param={"id":user_id}
     output=await postgres_client.fetch_all(query=query,values=query_param)
     user=output[0]
   #create token
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#auth/login-email-password
@app.get("/auth/login-email-password")
async def auth_login_email_password(request:Request,email:str,password:str):
   #read user
   query=f"select * from users where email=:email and password=:password order by id desc limit 1;"
   query_param={"email":email,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create token
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#auth/login-mobile-password
@app.get("/auth/login-mobile-password")
async def auth_login_mobile_password(request:Request,mobile:str,password:str):
   #read user
   query=f"select * from users where mobile=:mobile and password=:password order by id desc limit 1;"
   query_param={"mobile":mobile,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create token
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#my/profile
@app.get("/my/profile")
async def my_profile(request:Request,background:BackgroundTasks):
   #refresh request user
   output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   request.state.user=output[0] if output else None
   if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #update last active at
   query="update users set last_active_at=:last_active_at where id=:id"
   query_param={"id":request.state.user["id"],"last_active_at":datetime.datetime.now()}
   background.add_task(await postgres_client.fetch_all(query=query,values=query_param))
   #final
   return {"status":1,"message":request.state.user}

#my/token-refresh
@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   #refresh request user
   output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   request.state.user=output[0] if output else None
   if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create token
   user=request.state.user
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"],"api_access":user["api_access"]},default=str)
   token=jwt.encode({"exp":time.time()+10000600000,"data":data},os.getenv("secret_key_jwt"))
   #final
   return {"status":1,"message":token}

#my/update-password
@app.put("/my/update-password")
async def my_update_password(request:Request,password:str):
   #logic
   query="update users set password=:password,updated_by_id=:updated_by_id where id=:id returning *;"
   query_param={"id":request.state.user["id"],"password":hashlib.sha256(password.encode()).hexdigest(),"updated_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#admin/update-password
@app.put("/admin/update-password")
async def admin_update_password(request:Request,user_id:int,password:str):
   #logic
   query="update users set password=:password,updated_by_id=:updated_by_id where id=:id returning *;"
   query_param={"id":user_id,"password":hashlib.sha256(password.encode()).hexdigest(),"updated_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#root/update-password
@app.put("/root/update-password")
async def root_update_password(request:Request,user_id:int,password:str):
   #logic
   query="update users set password=:password where id=:id returning *;"
   query_param={"id":user_id,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#my/update-email
@app.put("/my/update-email")
async def my_update_email(request:Request,email:str,otp:int):
   #verify otp
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
   query_param={"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #logic
   query="update users set email=:email,updated_by_id=:updated_by_id where id=:id returning *;"
   query_param={"id":request.state.user["id"],"email":email,"updated_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#my/update-mobile
@app.put("/my/update-mobile")
async def my_update_mobile(request:Request,mobile:str,otp:int):
   #verify otp
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
   query_param={"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #logic
   query="update users set mobile=:mobile,updated_by_id=:updated_by_id where id=:id returning *;"
   query_param={"id":request.state.user["id"],"mobile":mobile,"updated_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#my/delete-ids
@app.delete("/my/delete-ids")
async def my_delete_ids(request:Request,table:str,ids:str):
   #check      
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if len(ids.split(","))>3:return responses.JSONResponse(status_code=400,content={"status":0,"message":"ids length not allowed"})
   #logic
   query=f"delete from {table} where created_by_id=:created_by_id and id in ({ids});"
   query_param={"created_by_id":request.state.user["id"]}
   await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":"done"}

#my/delete-account
@app.delete("/my/delete-account")
async def my_delete_account(request:Request,mode:str=None):
   output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   request.state.user=output[0] if output else None
   if not request.state.user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #check
   if request.state.user["id"]==1:return responses.JSONResponse(status_code=200,content={"status":0,"message":"root user cant be deleted"})
   if request.state.user["is_protected"]==1:return responses.JSONResponse(status_code=200,content={"status":0,"message":"protected user cant be deleted"})
   if request.state.user["api_access"]:return responses.JSONResponse(status_code=200,content={"status":0,"message":"admin user cant be deleted"})
   #logic
   if not mode:await postgres_client.fetch_all(query="delete from users where id=:id;",values={"id":request.state.user["id"]})
   if mode=="procedure":await postgres_client.fetch_all(query=f"call procedure_delete_user({request.state.user['id']});",values={})
   #final
   return {"status":1,"message":"account deleted"}

#my/object-create
@app.post("/my/object-create")
async def my_object_create(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   object["created_by_id"]=request.state.user["id"]
   #object check
   for k,v in object.items():
      if k in ["id","created_at","updated_at","updated_by_id","is_active","is_verified","is_deleted","password","google_id","otp"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{k} not allowed"})
   #serialize
   if is_serialize:
      response=await postgres_serialize([object],postgres_column_datatype)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud("create",table,[object],postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

#my/object-update
@app.put("/my/object-update")
async def my_object_update(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   #object check
   for k,v in object.items():
      if k in ["created_at","created_by_id","is_active","is_verified","type","google_id","otp","api_access"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{k} not allowed"})
   if table=="users" and "email" in object:return responses.JSONResponse(status_code=400,content={"status":0,"message":"email not allowed"})
   if table=="users" and "mobile" in object:return responses.JSONResponse(status_code=400,content={"status":0,"message":"mobile not allowed"})
   #ownwership check
   if table=="users":
      if int(object["id"])!=request.state.user["id"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"object ownership issue"})
   if table!="users":
      query=f"select created_by_id from {table} where id=:id;"
      query_param={"id":int(object["id"])}
      output=await postgres_client.fetch_all(query=query,values=query_param)
      object_2=output[0] if output else None
      if not object_2:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no object"})
      if object_2["created_by_id"]!=request.state.user["id"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"object ownership issue"})
   #serialize
   if is_serialize:
      response=await postgres_serialize([object],postgres_column_datatype)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud("update",table,[object],postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

#my/object-delete
@app.delete("/my/object-delete")
async def my_object_delete(request:Request,table:str):
   #check
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   #parse object where
   object_where=dict(request.query_params)
   object_where["created_by_id"]=f"=,{request.state.user['id']}"
   response=await postgres_object_where_parse(object_where,postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await postgres_serialize([where_value],postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f"delete from {table} {where_string};"
   await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":"done"}

#my/object-read
@app.get("/my/object-read")
@cache(expire=60)
async def my_object_read(request:Request,table:str,order:str="id desc",limit:int=100,page:int=1):
   #parse object where
   object_where=dict(request.query_params)
   object_where["created_by_id"]=f"=,{request.state.user['id']}"
   response=await postgres_object_where_parse(object_where,postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await postgres_serialize([where_value],postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   output=await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":output}

#my/message-create
@app.post("/my/message-create")
async def my_message_create(request:Request,user_id:int,description:str):
   #delete ids
   query=f"insert into message (created_by_id,user_id,description) values (:created_by_id,:user_id,:description) returning *;"
   query_param={"created_by_id":request.state.user["id"],"user_id":user_id,"description":description}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#my/message-received
@app.get("/my/message-received")
async def my_message_received(request:Request,background:BackgroundTasks,order:str="id desc",limit:int=100,page:int=1):
   #read message
   query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #ids string from object
   ids_list=[str(item["id"]) for item in output]
   ids_string=",".join(ids_list)
   #mark read
   if ids_string:
      query=f"update message set is_read=:is_read,updated_by_id=:updated_by_id where id in ({ids_string});"
      query_param={"is_read":1,"updated_by_id":request.state.user["id"]}
      background.add_task(await postgres_client.fetch_all(query=query,values=query_param))
   #final
   return {"status":1,"message":output}

#my/message-received-unread
@app.get("/my/message-received-unread")
async def my_message_received_unread(request:Request,background:BackgroundTasks,order:str="id desc",limit:int=100,page:int=1):
   #read message
   query=f"select * from message where user_id=:user_id and is_read!=1 is null order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #ids string from object
   ids_list=[str(item["id"]) for item in output]
   ids_string=",".join(ids_list)
   #mark read
   if ids_string:
      query=f"update message set is_read=:is_read,updated_by_id=:updated_by_id where id in ({ids_string});"
      query_param={"is_read":1,"updated_by_id":request.state.user["id"]}
      background.add_task(await postgres_client.fetch_all(query=query,values=query_param))
   #final
   return {"status":1,"message":output}

#my/message-inbox
@app.get("/my/message-inbox")
async def my_message_inbox(request:Request,order:str="id desc",limit:int=100,page:int=1):
   #read inbox
   query=f'''
   with
   x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),
   y as (select max(id) as id from x group by unique_id),
   z as (select m.* from y left join message as m on y.id=m.id)
   select * from z order by {order} limit {limit} offset {(page-1)*limit};
   '''
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#my/message-inbox-unread
@app.get("/my/message-inbox-unread")
async def my_message_inbox_unread(request:Request,order:str="id desc",limit:int=100,page:int=1):
   #read inbox
   query=f'''
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

#my/message-thread
@app.get("/my/message-thread")
async def my_message_thread(request:Request,background:BackgroundTasks,user_id:int,order:str="id desc",limit:int=100,page:int=1):
   #read message thread
   query=f"select * from message where ((created_by_id=:user_1 and user_id=:user_2) or (created_by_id=:user_2 and user_id=:user_1)) order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_1":request.state.user["id"],"user_2":user_id}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #mark read
   query="update message set is_read=:is_read,updated_by_id=:updated_by_id where created_by_id=:created_by_id and user_id=:user_id returning *;"
   query_param={"is_read":1,"updated_by_id":request.state.user['id'],"created_by_id":user_id,"user_id":request.state.user["id"]}
   background.add_task(await postgres_client.fetch_all(query=query,values=query_param))
   #final
   return {"status":1,"message":output}

#my/delete-message-all
@app.delete("/my/delete-message-all")
async def my_delete_messag_all(request:Request):
   #logic
   query="delete from message where (created_by_id=:created_by_id or user_id=:user_id);"
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":"done"}

#my/delete-message-created
@app.delete("/my/delete-message-created")
async def my_delete_message_created(request:Request):
   #logic
   query="delete from message where created_by_id=:created_by_id;"
   query_param={"created_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":"done"}

#my/delete-message-received
@app.delete("/my/delete-message-received")
async def my_delete_message_received(request:Request):
   #logic
   query="delete from message where user_id=:user_id;"
   query_param={"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":"done"}

#my/delete-message-single
@app.delete("/my/delete-message-single")
async def my_delete_message_single(request:Request,id:int):
   #logic
   query="delete from message where id=:id and (created_by_id=:created_by_id or user_id=:user_id);"
   query_param={"id":id,"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":"done"}

#my/action-create
from typing import Literal
@app.post("/my/action-create")
async def my_action_create(request:Request,action:str,parent_table:str,parent_id:int,rating:float=None,description:str=None):
   #logic
   if action in ["action_like","action_bookmark","action_report","action_block","action_follow"]:
      query=f"insert into {action} (created_by_id,parent_table,parent_id) values (:created_by_id,:parent_table,:parent_id) returning *;"
      query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id}
   if action in ["action_rating"]:
      if not rating:return responses.JSONResponse(status_code=400,content={"status":0,"message":"rating is must"})
      query=f"insert into {action} (created_by_id,parent_table,parent_id,rating) values (:created_by_id,:parent_table,:parent_id,:rating) returning *;"
      query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id,"rating":rating}
   if action in ["action_comment"]:
      if not description:return responses.JSONResponse(status_code=400,content={"status":0,"message":"description is must"})
      query=f"insert into {action} (created_by_id,parent_table,parent_id,description) values (:created_by_id,:parent_table,:parent_id,:description) returning *;"
      query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id,"description":description}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#ex=my liked post
#my/action-read-parent
@app.get("/my/action-read-parent")
async def my_action_read_parent(request:Request,action:str,parent_table:str,order:str="id desc",limit:int=100,page:int=1):
   #logic
   query=f'''
   with
   x as (select parent_id from {action} where created_by_id=:created_by_id and parent_table=:parent_table order by {order} limit {limit} offset {(page-1)*limit})
   select pt.* from x left join {parent_table} as pt on x.parent_id=pt.id;
   '''
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#my/action-delete-parent
@app.delete("/my/action-delete-parent")
async def my_action_delete_parent(request:Request,action:str,parent_table:str,parent_id:int):
   #logic
   query=f"delete from {action} where created_by_id=:created_by_id and parent_table=:parent_table and parent_id=:parent_id;"
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":"done"}

#my/action-check-parent
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

#ex=users following me
#my/action-on-me-creator-read
@app.get("/my/action-on-me-creator-read")
async def my_action_on_me_creator_read(request:Request,action:str,order:str="id desc",limit:int=100,page:int=1):
   #logic
   query=f'''
   with 
   x as (select * from {action} where parent_table=:parent_table),
   y as (select created_by_id from x where parent_id=:parent_id order by {order} limit {limit} offset {(page-1)*limit})
   select u.* from y left join users as u on y.created_by_id=u.id;
   '''
   query_param={"parent_table":"users","parent_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#ex=users i action_follow and following me
#my/action-on-me-creator-read-mutual
@app.get("/my/action-on-me-creator-read-mutual")
async def my_action_on_me_creator_read_mutual(request:Request,action:str,order:str="id desc",limit:int=100,page:int=1):
   #logic
   query=f'''
   with 
   x as (select * from {action} where parent_table=:parent_table),
   y as (select created_by_id from {action} where created_by_id in (select parent_id from x where created_by_id=:created_by_id) and parent_id=:parent_id order by {order} limit {limit} offset {(page-1)*limit})
   select u.* from y left join users as u on y.created_by_id=u.id;
   '''
   query_param={"parent_table":"users","parent_id":request.state.user["id"],"created_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#public/langchain-txt-file-token-splitter
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import TokenTextSplitter
@app.get("/public/langchain-txt-file-token-splitter")
async def public_langchain_txt_file_token_splitter(request:Request,file_path:str):
   loader=TextLoader(file_path)
   document=loader.load()
   text=document[0].page_content
   splitter=TokenTextSplitter(encoding_name="cl100k_base",chunk_size=1000,chunk_overlap=100)
   chunks=splitter.split_text(text)
   return {"status":1,"message":chunks}

#public/langchain-txt-file-chunks-splitter-recursive
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
@app.get("/public/langchain-txt-file-chunks-splitter-recursive")
async def public_langchain_txt_file_chunks_splitter_recursive(request:Request,file_path:str):
   loader=TextLoader(file_path)
   document=loader.load()
   text=document[0].page_content
   splitter=RecursiveCharacterTextSplitter(separators=["\n\n", "\n", " ", ""],chunk_size=1000,chunk_overlap=200,length_function=len)
   chunks=splitter.split_text(text)
   return {"status":1,"message":chunks}

#public/langchain-txt-file-chunks-splitter
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
@app.get("/public/langchain-txt-file-chunks-splitter")
async def public_langchain_txt_file_chunks_splitter(request:Request,file_path:str):
   loader=TextLoader(file_path)
   document=loader.load()
   text=document[0].page_content
   splitter=CharacterTextSplitter(separator="\n\n",chunk_size=1000,chunk_overlap=200)
   chunks=splitter.split_text(text)
   return {"status":1,"message":chunks}

#public/langchain-webpage-loader
import os,bs4
from langchain_community.document_loaders import WebBaseLoader
@app.get("/public/langchain-webpage-loader")
async def public_langchain_webpage_loader(request:Request,webpage_url:str):
   os.environ['USER_AGENT']='myagent'
   loader=WebBaseLoader(web_paths=[webpage_url],bs_kwargs={"parse_only": bs4.SoupStrainer(class_="theme-doc-markdown markdown"),},bs_get_text_kwargs={"separator": " | ", "strip": True},)
   document_list=[]
   async for doc in loader.alazy_load():document_list.append(doc)
   return {"status":1,"message":document_list}

#public/langchain-html-loader
from langchain_community.document_loaders import BSHTMLLoader
@app.get("/public/langchain-html-loader")
async def public_langchain_html_loader(request:Request,file_path:str):
   loader=BSHTMLLoader(file_path)
   data=loader.load()
   return {"status":1,"message":data}

#public/langchain-json-loader
from langchain_community.document_loaders import JSONLoader
@app.get("/public/langchain-json-loader")
async def public_langchain_json_loader(request:Request,file_path:str):
   loader=JSONLoader(file_path=file_path,jq_schema='.data',text_content=False)
   data=loader.load()
   return {"status":1,"message":data}

#public/langchain-pdf-loader
from langchain_community.document_loaders import PyPDFLoader
@app.get("/public/langchain-pdf-loader")
async def public_langchain_pdf_loader(request:Request,file_path:str):
   loader=PyPDFLoader(file_path)
   document_list=[]
   async for page in loader.alazy_load():document_list.append(page)
   return {"status":1,"message":document_list}

#public/langchain-csv-loader
from langchain_community.document_loaders.csv_loader import CSVLoader
@app.get("/public/langchain-csv-loader")
async def public_langchain_csv_loader(request:Request,file_path:str):
   loader=CSVLoader(file_path=file_path)
   document=loader.load()
   data=document[0].page_content
   return {"status":1,"message":document}

#public/langchain-directory-loader
from langchain_community.document_loaders import TextLoader,DirectoryLoader
@app.get("/public/langchain-directory-loader")
async def public_langchain_directory_loader(request:Request,directory_path:str,glob:str):
   loader=DirectoryLoader(directory_path,glob=glob,loader_cls=TextLoader,use_multithreading=True,show_progress=True)
   documents=loader.load()
   return {"status":1,"message":len(documents)}

#public/langchain-txt-file-loader
from langchain_community.document_loaders import TextLoader
@app.get("/public/langchain-txt-file-loader")
async def public_langchain_txt_file_loader(request:Request,file_path:str):
   loader=TextLoader(file_path)
   document=loader.load()
   text=document[0].page_content
   return {"status":1,"message":text}

#public/text-to-txt-file
@app.get("/public/text-to-txt-file")
async def public_text_to_txt_file(request:Request,text:str,file_path:str):
   with open(file_path,"w",encoding="utf-8") as file:file.write(text)
   return {"status":1,"message":"done"}

#public/opensearch-read-document
from opensearchpy import OpenSearch
@app.get("/public/opensearch-read-document")
async def public_opensearch_read_document(request:Request,index:str,keyword:str):
   opensearch_client=OpenSearch(os.getenv("opensearch_url"),use_ssl=True)
   query={'size':5,'query':{'multi_match':{'query':keyword}}}
   output=opensearch_client.search(body=query,index=index)
   return {"status":1,"message":output}

#public/opensearch-delete-document
from opensearchpy import OpenSearch
@app.delete("/public/opensearch-delete-document")
async def public_opensearch_delete_document(request:Request,index:str,_id:str):
   opensearch_client=OpenSearch(os.getenv("opensearch_url"),use_ssl=True)
   output=opensearch_client.delete(index=index,id=_id)
   return {"status":1,"message":output}

#public/opensearch-create-document
from opensearchpy import OpenSearch
@app.post("/public/opensearch-create-document")
async def public_opensearch_create_document(request:Request,index:str):
   opensearch_client=OpenSearch(os.getenv("opensearch_url"),use_ssl=True)
   object=await request.json()
   object_json=json.dumps(object)
   output=opensearch_client.index(index=index,body=object_json,refresh=True)
   return {"status":1,"message":output}

#public/opensearch-create-index
from opensearchpy import OpenSearch
@app.get("/public/opensearch-create-index")
async def public_opensearch_create_index(request:Request,index:str):
   opensearch_client=OpenSearch(os.getenv("opensearch_url"),use_ssl=True)
   output=opensearch_client.indices.create(index,body={'settings':{'index':{'number_of_shards':4}}})
   return {"status":1,"message":output}

#public/postgres-prepared-statement
@app.get("/public/postgres-prepared-statement")
async def public_postgres_prepared_statement(request:Request):
   query="select * from pg_prepared_statements where name='read_user';"
   output=await postgres_client.fetch_all(query=query,values={})
   if not output:
      query="prepare read_user (int) as select * from users where id=$1;"
      await postgres_client.fetch_all(query=query,values={})
   query="explain analyze select * from users where id=1;"
   output_1=await postgres_client.fetch_all(query=query,values={})
   query="explain analyze execute read_user(1);"
   output_2=await postgres_client.fetch_all(query=query,values={})
   output={"simple":output_1,"prepared":output_2}
   return {"status":1,"message":output}

#root/memcached-set-object
from pymemcache.client.hash import HashClient
@app.post("/root/memcached-set-object")
async def root_memcached_set_object(request:Request,key:str,expiry:int=None):
   memcached_client=HashClient(['127.0.0.1:11211','127.0.0.1:11212',])
   object=await request.json()
   object=json.dumps(object)
   if expiry:output=memcached_client.set(key,object,expiry)
   else:output=memcached_client.set(key,object)
   return {"status":1,"message":output}

#root/memcached-get-object
from pymemcache.client.hash import HashClient
@app.get("/root/memcached-get-object")
async def root_memcached_get_object(request:Request,key:str):
   memcached_client=HashClient(['127.0.0.1:11211','127.0.0.1:11212',])
   output=memcached_client.get("post_1")
   if output:output=json.loads(output)
   return {"status":1,"message":output}

#root/valkey-set-object
import valkey
@app.post("/root/valkey-set-object")
async def root_valkey_set_object(request:Request,key:str,expiry:int=None):
   valkey_client=valkey.from_url(os.getenv("valkey_server_url"))
   object=await request.json()
   object=json.dumps(object)
   if expiry:output=valkey_client.setex(key,expiry,object)
   else:output=valkey_client.set(key,object)
   valkey_client.close()
   return {"status":1,"message":output}

#root/valkey-get-object
import valkey
@app.get("/root/valkey-get-object")
async def root_valkey_get_object(request:Request,key:str):
   valkey_client=valkey.from_url(os.getenv("valkey_server_url"))
   output=valkey_client.get("post_1")
   if output:output=json.loads(output)
   valkey_client.close()
   return {"status":1,"message":output}

#root/redis-set-object
import redis.asyncio as redis
@app.post("/root/redis-set-object")
async def root_redis_set_object(request:Request,key:str,expiry:int=None):
   redis_client=redis.from_url(os.getenv("redis_server_url"))
   object=await request.json()
   object=json.dumps(object)
   if expiry:output=await redis_client.setex(key,expiry,object)
   else:output=await redis_client.set(key,object)
   await redis_client.aclose()
   return {"status":1,"message":output}

#root/redis-get-object
import redis.asyncio as redis
@app.get("/root/redis-get-object")
async def root_redis_get_object(request:Request,key:str):
   redis_client=redis.from_url(os.getenv("redis_server_url"))
   output=await redis_client.get("post_1")
   if output:output=json.loads(output)
   await redis_client.aclose()
   return {"status":1,"message":output}

#root/redis-flush
import redis.asyncio as redis
@app.delete("/root/redis-flush")
async def root_redis_flush(request:Request):
   redis_client=redis.from_url(os.getenv("redis_server_url"))
   output=await redis_client.flushall()
   await redis_client.aclose()
   return {"status":1,"message":output}

#root/redis-info
import redis.asyncio as redis
@app.get("/root/redis-info")
async def root_redis_info(request:Request):
   redis_client=redis.from_url(os.getenv("redis_server_url"))
   output=await redis_client.info()
   await redis_client.aclose()
   return {"status":1,"message":output}

#root/redis-publish
import redis.asyncio as redis
@app.post("/root/redis-publish")
async def root_redis_publish(request:Request,channel:str):
   redis_client=redis.from_url(os.getenv("redis_server_url"))
   object=await request.json()
   object=json.dumps(object)
   output=await redis_client.publish(channel,object)
   await redis_client.aclose()
   return {"status":1,"message":output}

#root/redis-transaction
import redis.asyncio as redis
@app.post("/root/redis-transaction")
async def root_redis_transaction(request:Request,expiry:int=None):
   redis_client=redis.from_url(os.getenv("redis_server_url"))
   body=await request.json()
   object_list=body["data"]
   key_list=body["key"]
   async with redis_client.pipeline(transaction=True) as pipe:
      for index,object in enumerate(object_list):
         if expiry:pipe.setex(key_list[index],expiry,json.dumps(object))
         else:pipe.set(key_list[index],json.dumps(object))
      await pipe.execute()
   await redis_client.aclose()
   return {"status":1,"message":"done"}

#root/redis-csv-set
import redis.asyncio as redis
@app.post("/root/redis-csv-set")
async def root_redis_csv_set(request:Request,file:UploadFile,table:str,expiry:int=None):
   redis_client=redis.from_url(os.getenv("redis_server_url"))
   file_csv=csv.DictReader(codecs.iterdecode(file.file,'utf-8'))
   object_list=[]
   for row in file_csv:object_list.append(row)
   await file.close()
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if expiry:pipe.setex(key,expiry,json.dumps(object))
         else:pipe.set(key,json.dumps(object))
      await pipe.execute()
   await redis_client.aclose()
   return {"status":1,"message":"done"}

#public/mongodb-delete
import motor.motor_asyncio
from bson.objectid import ObjectId
@app.delete("/public/mongodb-delete")
async def public_mongodb_delete(request:Request,database:str,collection:str,_id:str):
   mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(os.getenv("mongodb_cluster_url"))
   database=mongodb_client[database]
   collection=database[collection]
   _id=ObjectId(_id)
   output=await collection.delete_one({"_id":_id})
   return {"status":1,"message":str(output)}

#public/mongodb-update
import motor.motor_asyncio
from bson.objectid import ObjectId
@app.put("/public/mongodb-update")
async def public_mongodb_update(request:Request,database:str,collection:str,_id:str):
   mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(os.getenv("mongodb_cluster_url"))
   database=mongodb_client[database]
   collection=database[collection]
   _id=ObjectId(_id)
   object=await request.json()
   output=await collection.update_one({"_id":_id},{"$set":object})
   return {"status":1,"message":str(output)}

#public/mongodb-read
import motor.motor_asyncio
from bson.objectid import ObjectId
@app.get("/public/mongodb-read")
async def public_mongodb_read(request:Request,database:str,collection:str,_id:str):
   mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(os.getenv("mongodb_cluster_url"))
   database=mongodb_client[database]
   collection=database[collection]
   _id=ObjectId(_id)
   output=await collection.find_one({"_id":_id})
   return {"status":1,"message":str(output)}

#public/mongodb-create
import motor.motor_asyncio
@app.post("/public/mongodb-create")
async def public_mongodb_create(request:Request,database:str,collection:str):
   mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(os.getenv("mongodb_cluster_url"))
   database=mongodb_client[database]
   collection=database[collection]
   object=await request.json()
   output=await collection.insert_many([object])
   return {"status":1,"message":str(output)}

#root/kafka-producer
from aiokafka import AIOKafkaProducer
from aiokafka.helpers import create_ssl_context
@app.post("/root/kafka-producer")
async def root_kafka_producer(request:Request,topic:str):
   kafka_producer_client=AIOKafkaProducer(bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=create_ssl_context(cafile=os.getenv("kafka_path_cafile"),certfile=os.getenv("kafka_path_certfile"),keyfile=os.getenv("kafka_path_keyfile")))
   await kafka_producer_client.start()
   object=await request.json()
   object=json.dumps(object,indent=2).encode('utf-8')
   output=await kafka_producer_client.send_and_wait(topic,object,partition=0)
   await kafka_producer_client.stop()
   return {"status":1,"message":output}

#root/lavinmq-producer
import pika
@app.post("/root/lavinmq-producer")
async def root_lavinmq_producer(request:Request,queue:str):
   lavinmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("lavinmq_server_url")))
   channel=lavinmq_client.channel()
   channel.queue_declare(queue=queue)
   object=await request.json()
   object=json.dumps(object)
   channel.basic_publish(exchange='',routing_key=queue,body=object)
   lavinmq_client.close()
   return {"status":1,"message":"done"}

#root/rabbitmq-producer
import pika
@app.post("/root/rabbitmq-producer")
async def root_rabbitmq_producer(request:Request,queue:str):
   rabbitmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("rabbitmq_server_url")))
   channel=rabbitmq_client.channel()
   channel.queue_declare(queue=queue)
   object=await request.json()
   object=json.dumps(object)
   channel.basic_publish(exchange='',routing_key=queue,body=object)
   rabbitmq_client.close()
   return {"status":1,"message":"done"}

#root/ftp-list-dir-item
import ftplib
@app.get("/root/ftp-list-dir-item")
async def root_ftp_list_dir_item(request:Request,dir_path:str):
   ftp_client=ftplib.FTP(os.getenv("ftp_host"),os.getenv("ftp_username"),os.getenv("ftp_password"),os.getenv("ftp_port"))
   ftp_client.cwd(dir_path)
   output=ftp_client.nlst()
   ftp_client.quit()
   return {"status":1,"message":output}

#root/ftp-mkdir
import ftplib
@app.post("/root/ftp-mkdir")
async def root_ftp_mkdir(request:Request,dir_path:str,dir_name:str):
   ftp_client=ftplib.FTP(os.getenv("ftp_host"),os.getenv("ftp_username"),os.getenv("ftp_password"),os.getenv("ftp_port"))
   ftp_client.cwd(dir_path)
   ftp_client.mkd(dir_name)
   ftp_client.quit()
   return {"status":1,"message":"done"}

#root/ftp-upload-file
import ftplib
@app.post("/root/ftp-upload-file")
async def root_ftp_upload_file(request:Request,dir_path:str,file:UploadFile):
   ftp_client=ftplib.FTP(os.getenv("ftp_host"),os.getenv("ftp_username"),os.getenv("ftp_password"),os.getenv("ftp_port"))
   ftp_client.cwd(dir_path)
   ftp_client.storbinary(f"STOR {file.filename}",file.file)
   ftp_client.quit()
   return {"status":1,"message":"done"}

#root/ftp-rename-file
import ftplib
@app.put("/root/ftp-rename-file")
async def root_ftp_rename_file(request:Request,dir_path:str,filename_old:str,filename_new:str):
   ftp_client=ftplib.FTP(os.getenv("ftp_host"),os.getenv("ftp_username"),os.getenv("ftp_password"),os.getenv("ftp_port"))
   ftp_client.cwd(dir_path)
   ftp_client.rename(filename_old,filename_new) 
   ftp_client.quit()
   return {"status":1,"message":"done"}

#root/ftp-delete-file
import ftplib
@app.delete("/root/ftp-delete-file")
async def root_ftp_delete_file(request:Request,dir_path:str,filename:str):
   ftp_client=ftplib.FTP(os.getenv("ftp_host"),os.getenv("ftp_username"),os.getenv("ftp_password"),os.getenv("ftp_port"))
   ftp_client.cwd(dir_path)
   ftp_client.delete(filename)
   ftp_client.quit()
   return {"status":1,"message":"done"}

#root/ftp-delete-dir
import ftplib
@app.delete("/root/ftp-delete-dir")
async def root_ftp_delete_dir(request:Request,dir_path:str,dir_name:str):
   ftp_client=ftplib.FTP(os.getenv("ftp_host"),os.getenv("ftp_username"),os.getenv("ftp_password"),os.getenv("ftp_port"))
   ftp_client.cwd(dir_path)
   ftp_client.rmd(dir_name)
   ftp_client.quit()
   return {"status":1,"message":"done"}

#root/timescaledb-create-table
from databases import Database
@app.get("/root/timescaledb-create-table")
async def root_timescaledb_create_table(request:Request):
   timescaledb_client=Database(os.getenv("timescaledb_url"),min_size=1,max_size=100) 
   timescaledb_client.connect()
   query="create table event (created_at timestamptz default now() not null, type text not null, data jsonb not null);"
   await timescaledb_client.execute(query=query,values={})
   query="select create_hypertable('event', by_range('created_at'));"
   output=await timescaledb_client.fetch_all(query=query,values={})
   return {"status":1,"message":output}

#root/timescaledb-create-event
from databases import Database
@app.post("/root/timescaledb-create-event")
async def root_timescaledb_create_event(request:Request,type:str):
   timescaledb_client=Database(os.getenv("timescaledb_url"),min_size=1,max_size=100) 
   timescaledb_client.connect()
   object=await request.json()
   object_json=json.dumps(object)
   query="insert into event (type,data) values (:type,:data) returning *;"
   query_param={"type":type,"data":object_json}
   output=await timescaledb_client.fetch_all(query=query,values=query_param)
   timescaledb_client.disconnect()
   return {"status":1,"message":output}

#public/meilisearch-search
import meilisearch
@app.get("/public/meilisearch-search")
async def public_meilisearch_search(request:Request,index:str,keyword:str):
   meilisearch_client=meilisearch.Client(os.getenv("meilisearch_url"),os.getenv("meilisearch_key"))
   index=meilisearch_client.index(index)
   output=index.search(keyword)
   return {"status":1,"message":output}

#public/html-group-chat
from fastapi.responses import HTMLResponse
@app.get("/public/html-group-chat")
async def public_html_group_chat():
    html="""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Chat</title>
        </head>
        <body>
            <h1>Group Chat</h1>
            <h2>Your ID=<span id="client_id"></span></h2>
            <form action="" onsubmit="sendMessage(event)">
                <input type="text" id="messageText" autocomplete="off"/>
                <button>Send</button>
            </form>
            <ul id='messages'>
            </ul>
            <script> 
                var client_id = Date.now()
                document.querySelector("#client_id").textContent = client_id;
                var ws = new WebSocket(`ws://localhost:8000/public/websocket-group-chat/${client_id}`);
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                function sendMessage(event) {
                    var input = document.getElementById("messageText")
                    ws.send(input.value)
                    input.value = ''
                    event.preventDefault()
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(html)
 
#websocket group chat
from fastapi import WebSocket,WebSocketDisconnect
websocket_connection_list=[]
@app.websocket("/public/websocket-group-chat/{client_id}")
async def public_websocket_group_chat(websocket:WebSocket,client_id:int):
    await websocket.accept()
    websocket_connection_list.append(websocket)
    try:
        while True:
            message=await websocket.receive_text()
            for connection in websocket_connection_list:
                await connection.send_text(message)
    except WebSocketDisconnect:
        websocket_connection_list.remove(websocket)
        for connection in websocket_connection_list:
             await connection.send_text(f"{client_id} left the chat")
 
#public/html-single-chat
from fastapi.responses import HTMLResponse
@app.get("/public/html-single-chat/{user_id_1}/{user_id_2}")
async def public_html_single_chat(user_id_1:int,user_id_2:int):
   html=f"""
   <!DOCTYPE html>
   <html>
      <head>
         <title>Chat</title>
      </head>
      <body>
         <h1>Single Chat</h1>
         <h2>Your ID: <span id="client_id"></span></h2>
         <form action="" onsubmit="sendMessage(event)">
               <input type="text" id="messageText" autocomplete="off"/>
               <button>Send</button>
         </form>
         <ul id='messages'>
         </ul>
         <script>
               document.querySelector("#client_id").textContent = {user_id_1};
               var ws = new WebSocket(`ws://localhost:8000/public/websocket-single-chat/{user_id_1}/{user_id_2}`);
               ws.onmessage = function(event) {{
                  var messages = document.getElementById('messages')
                  var message = document.createElement('li')
                  var content = document.createTextNode(event.data)
                  message.appendChild(content)
                  messages.appendChild(message)
               }};
               function sendMessage(event) {{
                  var input = document.getElementById("messageText")
                  ws.send(input.value)
                  input.value = ''
                  event.preventDefault()
               }}
         </script>
      </body>
   </html>
   """
   return HTMLResponse(html)
 
#websocket single chat
from fastapi import WebSocket,WebSocketDisconnect
websocket_connection_dict={}
@app.websocket("/public/websocket-single-chat/{user_id_1}/{user_id_2}")
async def public_websocket_single_chat(websocket:WebSocket,user_id_1:int,user_id_2:int):
    await websocket.accept()
    websocket_connection_dict[user_id_1]=websocket
    try:
        while True:
            message=await websocket.receive_text()
            if user_id_2 in websocket_connection_dict:
               await websocket_connection_dict[user_id_1].send_text(f"{user_id_1}-{message}")
               await websocket_connection_dict[user_id_2].send_text(f"{user_id_1}-{message}")
            else:await websocket_connection_dict[user_id_1].send_text(f"{user_id_2} offline")
    except WebSocketDisconnect:
       websocket_connection_dict.pop(user_id_1, None)
       if user_id_2 in websocket_connection_dict:await websocket_connection_dict[user_id_2].send_text(f"{user_id_1} left the chat")
       else:await websocket_connection_dict[user_id_1].send_text(f"{user_id_1} left the chat")
             
#public/object-create
@app.post("/public/object-create")
async def public_object_create(request:Request,table:Literal["helpdesk"],is_serialize:int=1):
   #object set
   object=await request.json()
   #serialize
   if is_serialize:
      response=await postgres_serialize([object],postgres_column_datatype)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud("create",table,[object],postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

#public/api-list
@app.get("/public/api-list")
async def public_api_list(request:Request,mode:str=None):
   #logic
   api_list=[route.path for route in router.routes]
   if mode=="admin":api_list=[route.path for route in router.routes if "/admin" in route.path]
   #final
   return {"status":1,"message":api_list}

#public/table-column
@app.get("/public/table-column")
async def public_table_column(request:Request,table:str=None):
   #table
   output=await postgres_client.fetch_all(query="select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE';",values={})
   table_name_list=[item["table_name"] for item in output]
   temp={}
   for item in table_name_list:temp[item]={}
   #columm
   query_master='''
   with 
   t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),
   c as (select * from information_schema.columns where table_schema='public')
   select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name
   '''
   output=await postgres_client.fetch_all(query=query_master,values={})
   for item in output:temp[item["table_name"]][item["column_name"]]=item["data_type"]
   #if table
   if table:temp=temp[table]
   #final
   return {"status":1,"message":temp}

#public/project meta
@app.get("/public/project-meta")
@cache(expire=60)
async def public_project_meta(request:Request):
   #logic
   query_dict={"user_count":"select count(*) from users;"}
   temp={k:await postgres_client.fetch_all(query=v,values={}) for k,v in query_dict.items()}
   response={"status":1,"message":temp}
   #final
   return response

# #public/cassandra-version
# from cassandra.cluster import Cluster
# from cassandra.auth import PlainTextAuthProvider
# @app.get("/public/cassandra-version")
# async def public_cassandra_version(request:Request):
#    #logic
#    cassandra_cluster=Cluster(cloud={'secure_connect_bundle':os.getenv("cassandra_scb_path")},auth_provider=PlainTextAuthProvider(os.getenv("cassandra_client_id"),os.getenv("cassandra_secret_key")))
#    cassandra_client=cassandra_cluster.connect()
#    row=cassandra_client.execute("select release_version from system.local").one()
#    if row:output=row[0]
#    #final
#    return {"status":1,"message":output}

#public/otp send mobile sns
import boto3,random
@app.get("/public/otp-send-mobile-sns")
async def public_otp_send_mobile_sns(request:Request,region:str,mobile:str,entity_id:str=None,sender_id:str=None,template_id:str=None,message:str=None):
   #create otp
   otp=random.randint(100000,999999)
   query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;"
   query_param={"otp":otp,"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #send otp
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   if not entity_id:output=sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   else:output=sns_client.publish(PhoneNumber=mobile,Message=message.replace("{otp}",str(otp)),MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   #final
   return {"status":1,"message":output}

#public/otp send email ses
import boto3
@app.get("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request,region:str,sender:str,email:str):
   #create otp
   otp=random.randint(100000,999999)
   query="insert into otp (otp,email) values (:otp,:email) returning *;"
   query_param={"otp":otp,"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #send otp
   to,title,body=[email],"otp from atom",str(otp)
   ses_client=boto3.client("ses",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=ses_client.send_email(Source=sender,Destination={"ToAddresses":to},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   #final
   return {"status":1,"message":"done"}

#public/otp verify email
@app.get("/public/otp-verify-email")
async def public_otp_verify_email(request:Request,email:str,otp:int):
   #logic
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
   query_param={"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #final
   return {"status":1,"message":"done"}

#public/otp verify mobile
@app.get("/public/otp-verify-mobile")
async def public_otp_verify_mobile(request:Request,mobile:str,otp:int):
   #logic
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
   query_param={"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #final
   return {"status":1,"message":"done"}

#public/object read
@app.get("/public/object-read")
@cache(expire=60)
async def public_object_read(request:Request,table:str,order:str="id desc",limit:int=100,page:int=1):
   #check table
   if table not in ["users","post","atom","box"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   #parse object where
   object_where=dict(request.query_params)
   response=await postgres_object_where_parse(object_where,postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await postgres_serialize([where_value],postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #read object
   query=f'''
   with
   x as (select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit})
   select x.*,u.username as created_by_id_username from x left join users as u on x.created_by_id=u.id;
   '''
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   #add action_like count
   response=await postgres_add_action_count("action_like",table,object_list,postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   object_list=response["message"]
   #add action_bookmark count
   response=await postgres_add_action_count("action_bookmark",table,object_list,postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   object_list=response["message"]
   #final
   return {"status":1,"message":object_list}

#private/search-location
@app.get("/private/search-location")
async def private_location_search(request:Request,table:str,location:str,within:str,order:str="id desc",limit:int=100,page:int=1):
   #start
   long,lat=float(location.split(",")[0]),float(location.split(",")[1])
   min_meter,max_meter=int(within.split(",")[0]),int(within.split(",")[1])
   #parse object where
   object_where=dict(request.query_params)
   response=await postgres_object_where_parse(object_where,postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await postgres_serialize([where_value],postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f'''
   with
   x as (select * from {table} {where_string}),
   y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x)
   select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};
   '''
   output=await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":output}

#private/object read
@app.get("/private/object-read")
@cache(expire=60)
async def private_object_read(request:Request,table:str,order:str="id desc",limit:int=100,page:int=1):
   #check table
   if table not in ["users","post","atom","box"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   #parse object where
   object_where=dict(request.query_params)
   response=await postgres_object_where_parse(object_where,postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await postgres_serialize([where_value],postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #logic
   query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   output=await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":output}

#private/s3 upload file
import boto3
@app.post("/private/s3-upload-file")
async def private_s3_upload_file(request:Request,bucket:str,file:UploadFile):
   #logic
   key=str(uuid.uuid4())+"-"+file.filename
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_client.upload_fileobj(file.file,bucket,key)
   url=f"https://{bucket}.s3.amazonaws.com/{key}"
   #final
   return {"status":1,"message":url}

#private/s3 upload file multipart
import boto3
from boto3.s3.transfer import TransferConfig
@app.post("/private/s3-upload-file-multipart")
async def private_s3_upload_file_multipart(request:Request,bucket:str,file_path:str):
   #logic
   file_name=file_path.rsplit("/",1)[-1]
   key=str(uuid.uuid4())+"-"+file_name
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_client.upload_file(file_path,bucket,key,Config=TransferConfig(multipart_threshold=8000000))
   url=f"https://{bucket}.s3.amazonaws.com/{key}"
   #final
   return {"status":1,"message":url}

#private/s3 create presigned url
import boto3
@app.get("/private/s3-create-presigned-url")
async def private_s3_create_presigned_url(request:Request,region:str,bucket:str,filename:str):
   #logic
   if "." not in filename:return {"status":0,"message":"filename extension must"}
   key=str(uuid.uuid4())+"-"+filename
   expiry_sec=1000
   size_kb=250
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec,Conditions=[['content-length-range',1,size_kb*1024]])
   #final
   return {"status":1,"message":output}

#private/rekognition compare face
import boto3
@app.post("/private/rekognition-compare-face")
async def private_rekognition_compare_face(request:Request,region:str,file:list[UploadFile]):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   source_image={"Bytes":file[0].file.read()}
   target_image={"Bytes":file[1].file.read()}
   output=rekognition_client.compare_faces(SourceImage=source_image,TargetImage=target_image,SimilarityThreshold=80,QualityFilter='AUTO')
   #final
   return {"status":1,"message":output}

#private/rekognition detetct label
import boto3
@app.post("/private/rekognition-detect-label")
async def private_rekognition_detect_label(request:Request,region:str,file:UploadFile):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   image={"Bytes":file.file.read()}
   output=rekognition_client.detect_labels(Image=image,MaxLabels=10,MinConfidence=90)
   #final
   return {"status":1,"message":output}

#private/rekognition detetct face
import boto3
@app.post("/private/rekognition-detect-face")
async def private_rekognition_detect_face(request:Request,region:str,file:UploadFile):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   image={"Bytes":file.file.read()}
   output=rekognition_client.detect_faces(Image=image,Attributes=['BEARD','EYEGLASSES'])
   #final
   return {"status":1,"message":output}

#private/rekognition detect moderation
import boto3
@app.post("/private/rekognition-detect-moderation")
async def private_rekognition_detect_moderation(request:Request,region:str,file:UploadFile):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   image={"Bytes":file.file.read()}
   output=rekognition_client.detect_moderation_labels(Image=image,MinConfidence=80)
   #final
   return {"status":1,"message":output}

#private/rekognition detect text
import boto3
@app.post("/private/rekognition-detect-text")
async def private_rekognition_detect_text(request:Request,region:str,file:UploadFile):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   image={"Bytes":file.file.read()}
   output=rekognition_client.detect_text(Image=image)
   #final
   return {"status":1,"message":output}

#private/rekognition celebrity info
import boto3
@app.post("/private/rekognition-celebrity-info")
async def private_rekognition_celebrity_info(request:Request,region:str,celebrity_id:str):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=rekognition_client.get_celebrity_info(Id=celebrity_id)
   #final
   return {"status":1,"message":output}

#private/rekognition job start
import boto3
@app.post("/private/rekognition-job-start")
async def private_rekognition_job_start(request:Request,region:str,mode:Literal["celebrity","text","segment","label","face","content"],video_url:str):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   bucket=video_url.split("//",1)[1].split(".",1)[0]
   key=video_url.rsplit("/",1)[1]
   video={'S3Object':{'Bucket':bucket,'Name':key}}
   if mode=="celebrity":output=rekognition_client.start_celebrity_recognition(Video=video)
   if mode=="text":output=rekognition_client.start_text_detection(Video=video)
   if mode=="segment":output=rekognition_client.start_segment_detection(Video=video,SegmentTypes=['TECHNICAL_CUE'])
   if mode=="label":output=rekognition_client.start_label_detection(Video=video)
   if mode=="face":output=rekognition_client.start_face_detection(Video=video)
   if mode=="content":output=rekognition_client.start_content_moderation(Video=video)
   #final
   return {"status":1,"message":output}

#private/rekognition job status
import boto3
@app.post("/private/rekognition-job-status")
async def private_rekognition_job_status(request:Request,region:str,mode:Literal["celebrity","text","segment","label","face","content"],job_id:str,next_token:str=None):
   #logic
   rekognition_client=boto3.client("rekognition",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   if mode=="celebrity":
      if next_token:output=rekognition_client.get_celebrity_recognition(JobId=job_id,MaxResults=100,NextToken=next_token)
      else:output=rekognition_client.get_celebrity_recognition(JobId=job_id,MaxResults=100)
   if mode=="text":
      if next_token:output=rekognition_client.get_text_detection(JobId=job_id,MaxResults=100,NextToken=next_token)
      else:output=rekognition_client.get_text_detection(JobId=job_id,MaxResults=100)
   if mode=="segment":
      if next_token:output=rekognition_client.get_segment_detection(JobId=job_id,MaxResults=100,NextToken=next_token)
      else:output=rekognition_client.get_segment_detection(JobId=job_id,MaxResults=100)
   if mode=="label":
      if next_token:output=rekognition_client.get_label_detection(JobId=job_id,MaxResults=100,NextToken=next_token)
      else:output=rekognition_client.get_label_detection(JobId=job_id,MaxResults=100)
   if mode=="face":
      if next_token:output=rekognition_client.get_face_detection(JobId=job_id,MaxResults=100,NextToken=next_token)
      else:output=rekognition_client.get_face_detection(JobId=job_id,MaxResults=100)
   if mode=="content":
      if next_token:output=rekognition_client.get_content_moderation(JobId=job_id,MaxResults=100,NextToken=next_token)
      else:output=rekognition_client.get_content_moderation(JobId=job_id,MaxResults=100)
   #final
   return {"status":1,"message":output}

#private/openai
from langchain_community.llms import OpenAI
@app.get("/private/openai-prompt")
async def private_openai_prompt(request:Request,text:str):
   #logic
   llm=OpenAI(api_key=os.getenv("secret_key_openai"),temperature=0.7)
   output=llm(text)
   #final
   return {"status":1,"message":output}

#admin/update-api-access
from pydantic import BaseModel
class schema_update_api_access(BaseModel):
   user_id:int
   api_access:str|None=None
@app.put("/admin/update-api-access")
async def admin_update_api_access(request:Request,body:schema_update_api_access):
   #api list
   api_list=[route.path for route in request.app.routes]
   api_list_admin=[item for item in api_list if "/admin" in item]
   api_list_admin_str=",".join(api_list_admin)
   #check body
   if body.api_access:
      for item in body.api_access.split(","):
         if item not in api_list_admin_str:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wrong api access string"})
   #body modify
   if body.api_access=="":body.api_access=None
   #logic
   query="update users set api_access=:api_access where id=:id returning *"
   query_param={"id":body.user_id,"api_access":body.api_access}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#root/postgres clean
@app.delete("/root/postgres-clean")
async def root_pclean(request:Request):
   #table name
   output=await postgres_client.fetch_all(query="select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE';",values={})
   table_name_list=[item["table_name"] for item in output]
   table_name_list_action=[item for item in table_name_list if "action_" in item]
   #parent_table name
   parent_table_list=[]
   for item in table_name_list_action:
      output=await postgres_client.fetch_all(query=f"select distinct(parent_table) from {item};",values={})
      parent_table_list=parent_table_list+[item["parent_table"] for item in output]
   parent_table_name_list=list(set(parent_table_list))
   #creator null
   [await postgres_client.fetch_all(query=f"delete from {table} where created_by_id not in (select id from users);",values={}) for table in ["post","message"]+table_name_list_action]
   #parent null
   [await postgres_client.fetch_all(query=f"delete from {table} where parent_table='{parent_table}' and parent_id not in (select id from {parent_table});",values={}) for table in table_name_list_action for parent_table in parent_table_name_list]
   #final
   return {"status":1,"message":"done"}

#admin/csv-uploader 
@app.post("/admin/csv-uploader")
async def admin_csv_uploader(request:Request,file:UploadFile,mode:str,table:str,is_serialize:int=1):
   #object list
   if file.content_type!="text/csv":return {"status":0,"message":"file extension must be csv"}
   file_csv=csv.DictReader(codecs.iterdecode(file.file,'utf-8'))
   object_list=[]
   for row in file_csv:object_list.append(row)
   await file.close()
   #serialize
   if is_serialize:
      response=await postgres_serialize(object_list,postgres_column_datatype)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
   #logic
   response=await postgres_cud(mode,table,object_list,postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

#root/s3-delete-url
import boto3
@app.delete("/root/s3-delete-url")
async def root_s3_delete_url(request:Request,url:str):
   #logic
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   s3_resource=boto3.resource("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_resource.Object(bucket,key).delete()
   #final
   return {"status":1,"message":output}

#root/s3-delete-bucket
import boto3
@app.delete("/root/s3-delete-bucket")
async def root_s3_delete_bucket(request:Request,bucket:str):
   #logic
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_client.delete_bucket(Bucket=bucket)
   #final
   return {"status":1,"message":output}

#root/s3-empty-bucket
import boto3
@app.delete("/root/s3-empty-bucket")
async def root_s3_empty_bucket(request:Request,bucket:str):
   #logic
   s3_resource=boto3.resource("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_resource.Bucket(bucket).objects.all().delete()
   #final
   return {"status":1,"message":output}

#root/s3-list-all-bucket
import boto3
@app.get("/root/s3-list-all-bucket")
async def root_s3_list_all_bucket(request:Request):
   #logic
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_client.list_buckets()
   #final
   return {"status":1,"message":output}

#root/s3-create-bucket
import boto3
@app.post("/root/s3-create-bucket")
async def root_s3_create_bucket(request:Request,region:str,name:str):
   #logic
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=s3_client.create_bucket(Bucket=name,CreateBucketConfiguration={'LocationConstraint':region})
   #final
   return {"status":1,"message":output}

#root/s3-make-bucket-public
import boto3
@app.put("/root/s3-make-bucket-public")
async def root_s3_make_bucket_public(request:Request,bucket:str):
   #logic
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal": "*","Action": "s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   #final
   return {"status":1,"message":output}

#root/s3-download-url
import boto3
@app.get("/root/s3-download-url")
async def root_s3_download_url(request:Request,url:str,path:str):
   #logic
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   s3_client.download_file(bucket,key,path)
   #final
   return {"status":1,"message":"done"}

#admin/postgres-query-runner
@app.get("/admin/postgres-query-runner")
async def admin_postgres_query_runner(request:Request,query:str):
  #stop keywords
  for item in ["insert","update","delete","alter","drop"]:
    if item in query:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{item} not allowed in query"})
  #query run
  output=await postgres_client.fetch_all(query=query,values={})
  #final
  return {"status":1,"message":output}

#admin/object-read
@app.get("/admin/object-read")
async def admin_object_read(request:Request,table:str,order:str="id desc",limit:int=100,page:int=1):
   #parse object where
   object_where=dict(request.query_params)
   response=await postgres_object_where_parse(object_where,postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await postgres_serialize([where_value],postgres_column_datatype)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #read object
   query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   output=await postgres_client.fetch_all(query=query,values=where_value)
   response={"status":1,"message":output}
   #final
   return response

#admin/object-update
@app.put("/admin/object-update")
async def admin_object_update(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   #serialize
   if is_serialize:
      response=await postgres_serialize([object],postgres_column_datatype)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object=response["message"][0]
   #logic
   response=await postgres_cud("update",table,[object],postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #final
   return response

#admin/delete ids
@app.put("/admin/delete-ids")
async def admin_delete_ids(request:Request,table:str,ids:str):
   #logic
   query=f"delete from {table} where id in ({ids});"
   await postgres_client.fetch_all(query=query,values={})
   #final
   return {"status":1,"message":"done"}

#root/ses-add-identity
import boto3
@app.post("/root/ses-add-identity")
async def root_ses_add_identity(request:Request,region:str,type:Literal["email","domain"],identity:str):
   #logic
   ses_client=boto3.client("ses",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   if type=="email":output=ses_client.verify_email_identity(EmailAddress=identity)
   if type=="domain":output=ses_client.verify_domain_identity(Domain=identity)
   #final
   return {"status":1,"message":output}

#root/ses-list-identity
import boto3
@app.get("/root/ses-list-identity")
async def root_ses_list_identity(request:Request,region:str,type:Literal["EmailAddress","Domain"],limit:int,next_token:str=None):
   #logic
   ses_client=boto3.client("ses",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=ses_client.list_identities(IdentityType=type,NextToken='' if not next_token else next_token,MaxItems=limit)
   #final
   return {"status":1,"message":output}

#root/ses-identity-status
import boto3
@app.get("/root/ses-identity-status")
async def root_ses_identity_status(request:Request,region:str,identity:str):
   #logic
   ses_client=boto3.client("ses",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=ses_client.get_identity_verification_attributes(Identities=[identity])
   #final
   return {"status":1,"message":output}

#root/ses-delete-identity
import boto3
@app.delete("/root/ses-delete-identity")
async def root_ses_delete_identity(request:Request,region:str,identity:str):
   #logic
   ses_client=boto3.client("ses",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=ses_client.delete_identity(Identity=identity)
   #final
   return {"status":1,"message":output}

#root/sns-check-opted-out
import boto3
@app.get("/root/sns-check-opted-out")
async def root_sns_check_opted_out(request:Request,region:str,mobile:str):
   #logic
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=sns_client.check_if_phone_number_is_opted_out(phoneNumber=mobile)
   #final
   return {"status":1,"message":output}

#root/sns-list-opted-mobile
import boto3
@app.get("/root/sns-list-opted-mobile")
async def root_sns_list_opted_mobile(request:Request,region:str,next_token:str=None):
   #logic
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=sns_client.list_phone_numbers_opted_out(nextToken='' if not next_token else next_token)
   #final
   return {"status":1,"message":output}

#root/sns-list-sandbox-mobile
import boto3
@app.get("/root/sns-list-sandbox-mobile")
async def root_sns_list_sandbox_mobile(request:Request,region:str,limit:int=100,next_token:str=None):
   #logic
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   if not next_token:output=sns_client.list_sms_sandbox_phone_numbers(MaxResults=limit)
   else:output=sns_client.list_sms_sandbox_phone_numbers(NextToken=next_token,MaxResults=limit)
   #final
   return {"status":1,"message":output}

#root/sns-add-sandbox-mobile
import boto3
@app.get("/root/sns-add-sandbox-mobile")
async def root_sns_add_sandbox_mobile(request:Request,region:str,mobile:str):
   #logic
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=sns_client.create_sms_sandbox_phone_number(PhoneNumber=mobile,LanguageCode='en-US')
   #final
   return {"status":1,"message":output}

#root/sns-verify-sandbox-mobile
import boto3
@app.put("/root/sns-verify-sandbox-mobile")
async def root_sns_verify_sandbox_mobile(request:Request,region:str,mobile:str,otp:str):
   #logic
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=sns_client.verify_sms_sandbox_phone_number(PhoneNumber=mobile,OneTimePassword=otp)
   #final
   return {"status":1,"message":output}

#root/sns-optin-mobile
import boto3
@app.put("/root/sns-optin-mobile")
async def root_sns_optin_mobile(request:Request,region:str,mobile:str):
   #logic
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=sns_client.opt_in_phone_number(phoneNumber=mobile)
   #final
   return {"status":1,"message":output}

#root/sns-delete-sandbox-mobile
import boto3
@app.delete("/root/sns-delete-sandbox-mobile")
async def root_sns_delete_sandbox_mobile(request:Request,region:str,mobile:str):
   #logic
   sns_client=boto3.client("sns",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   output=sns_client.delete_sms_sandbox_phone_number(PhoneNumber=mobile)
   #final
   return {"status":1,"message":output}

#root/dynamodb-create-table
import boto3,json
@app.post("/root/dynamodb-create-table")
async def root_dynamodb_create_table(request:Request,region:str,name:str,hash:str,range:str,hash_data_type:str,range_data_type:str,read:int,write:int):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.create_table(TableName=name,KeySchema=[{"AttributeName":hash,"KeyType":"HASH"},{"AttributeName":range,"KeyType":"RANGE"}],AttributeDefinitions=[{"AttributeName":hash,"AttributeType":hash_data_type},{"AttributeName":range,"AttributeType":range_data_type}],ProvisionedThroughput={'ReadCapacityUnits':read,'WriteCapacityUnits':write})
   table.wait_until_exists()
   #final
   return {"status":1,"message":"done"}

#root/dynamodb-delete-table
import boto3,json
@app.delete("/root/dynamodb-delete-table")
async def root_dynamodb_delete_table(request:Request,region:str,name:str):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.Table(name)
   output=table.delete()
   #final
   return {"status":1,"message":output}

#root/dynamodb-create-item
import boto3
from decimal import Decimal
@app.post("/root/dynamodb-create-item")
async def root_dynamodb_create_item(request:Request,region:str,table:str):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.Table(table)
   object=await request.json()
   object={k:Decimal(str(v)) if type(v).__name__=="float" else v for k,v in object.items()}
   output=table.put_item(Item=object)
   #final
   return {"status":1,"message":output}

#root/dynamodb-create-item-batch
import boto3
@app.post("/root/dynamodb-create-item-batch")
async def root_dynamodb_create_item_batch(request:Request,region:str,table:str,hash:str,range:str):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.Table(table)
   object=await request.json()
   with table.batch_writer(overwrite_by_pkeys=[hash,range]) as batch:
      for item in object["data"]:batch.put_item(Item=item)
   #final
   return {"status":1,"message":"done"}

#root/dynamodb-read-item-pk
import boto3
@app.post("/root/dynamodb-read-item-pk")
async def root_dynamodb_read_item_pk(request:Request,region:str,table:str,hash:str,range:str):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.Table(table)
   object=await request.json()
   hash_value,range_value=object["hash_value"],object["range_value"]
   output=table.get_item(Key={hash:hash_value,range:range_value})
   #final
   return {"status":1,"message":output}

#root/dynamodb-read-item-attribute
import boto3
from boto3.dynamodb.conditions import Attr
@app.post("/root/dynamodb-read-item-attribute")
async def root_dynamodb_read_item_attribute(request:Request,region:str,table:str):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.Table(table)
   object=await request.json()
   attribute,value=object["attribute"],object["value"]
   output=table.scan(FilterExpression=Attr(attribute).eq(value))
   #final
   return {"status":1,"message":output}

#root/dynamodb-update-item
import boto3
@app.put("/root/dynamodb-update-item")
async def root_dynamodb_update_item(request:Request,region:str,table:str,hash:str,range:str):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.Table(table)
   object=await request.json()
   hash_value,range_value=object["hash_value"],object["range_value"]
   query,value=object["query"],object["value"]
   output=table.update_item(Key={hash:hash_value,range:range_value},UpdateExpression=query,ExpressionAttributeValues=value)
   #final
   return {"status":1,"message":output}

#root/dynamodb-delete-item
import boto3
@app.delete("/root/dynamodb-delete-item")
async def root_dynamodb_delete_item(request:Request,region:str,table:str,hash:str,range:str):
   #logic
   dynamodb_resource=boto3.resource("dynamodb",region_name=region,aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   table=dynamodb_resource.Table(table)
   object=await request.json()
   hash_value,range_value=object["hash_value"],object["range_value"]
   output=table.delete_item(Key={hash:hash_value,range:range_value})
   #final
   return {"status":1,"message":output}

#root/sqlite-query-runner
from databases import Database
@app.get("/root/sqlite-query-runner")
async def root_sqlite_query_runner(request:Request,mode:str,query:str):
   #client
   sqlite_client=Database('sqlite+aiosqlite:///atom.db')
   sqlite_client.connect()
   query_list=query.split("---")
   output="done"
   #logic
   if mode=="read":output=await sqlite_client.fetch_all(query=query,values={})
   if mode=="write":[await sqlite_client.execute(query=item,values={}) for item in query_list]
   #final
   sqlite_client.disconnect()
   return {"status":1,"message":output}

#mode
import sys
mode=sys.argv

#main fastapi app start
import asyncio,uvicorn
if __name__=="__main__" and len(mode)==1:
   try:
      asyncio.run(fastapi_app_start(app))
   except KeyboardInterrupt:
      print("exited")

#main redis subscriber start
import asyncio
if __name__=="__main__" and len(mode)>1 and mode[1]=="redis_subscribe":
   try:
      asyncio.run(redis_subscriber_start(os.getenv("redis_server_url"),mode[2]))
   except KeyboardInterrupt:
      print("exited")
   
#main kafka consumer start
import asyncio
if __name__=="__main__" and len(mode)>1 and mode[1]=="kafka_consumer":
   try:
      asyncio.run(kafka_consumer_start(os.getenv("kafka_server_url"),os.getenv("kafka_path_cafile"),os.getenv("kafka_path_certfile"),os.getenv("kafka_path_keyfile"),mode[2]))
   except KeyboardInterrupt:
      print("exited")

#main lavinmq consumer start
import asyncio,pika
if __name__=="__main__" and len(mode)>1 and mode[1]=="lavinmq_consumer":
   try:
      lavinmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("lavinmq_server_url")))
      channel=lavinmq_client.channel()
      channel.queue_declare(queue=mode[2])
      channel.basic_consume(mode[2],lavinmq_consumer_logic,auto_ack=True)
      channel.start_consuming()
   except KeyboardInterrupt:
      lavinmq_client.close()
      print("exited")

#main rabbitmq consumer start
import asyncio,pika
if __name__=="__main__" and len(mode)>1 and mode[1]=="rabbitmq_consumer":
   try:
      rabbitmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("rabbitmq_server_url")))
      channel=rabbitmq_client.channel()
      channel.queue_declare(queue=mode[2])
      channel.basic_consume(mode[2],rabbitmq_consumer_logic,auto_ack=True)
      channel.start_consuming()
   except KeyboardInterrupt:
      rabbitmq_client.close()
      print("exited")
      