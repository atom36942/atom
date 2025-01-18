#env
import os
from dotenv import load_dotenv
load_dotenv()

#function
secret_key_jwt=os.getenv("secret_key_jwt")
from fastapi import Request,Response
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param=str(dict(sorted(request.query_params.items())))
   user_id=0
   gate=api.split("/")[1]
   token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
   if gate=="my":user_id=json.loads(jwt.decode(token,secret_key_jwt,algorithms="HS256")["data"])["id"]
   key=api+"---"+str(user_id)+"---"+query_param
   return key

async def create_where_string(postgres_column_datatype,object):
   object={k:v for k,v in object.items() if k in postgres_column_datatype}
   object={k:v for k,v in object.items() if k not in ["location","metadata"]}
   object={k:v for k,v in object.items() if k not in ["table","order","limit","page"]}
   object_operator={k:v.split(',',1)[0] for k,v in object.items()}
   object_value={k:v.split(',',1)[1] for k,v in object.items()}
   column_read_list=[*object]
   where_column_single_list=[f"({column} {object_operator[column]} :{column} or :{column} is null)" for column in column_read_list]
   where_column_joined=' and '.join(where_column_single_list)
   where_string=f"where {where_column_joined}" if where_column_joined else ""
   where_value=object_value
   return {"status":1,"message":[where_string,where_value]}

import hashlib,datetime,json
async def object_serialize(postgres_column_datatype,object_list):
   for index,object in enumerate(object_list):
      for k,v in object.items():
         datatype=postgres_column_datatype[k]
         if not v:object_list[index][k]=None
         if k in ["password","google_id"]:object_list[index][k]=hashlib.sha256(v.encode()).hexdigest() if v else None
         if "int" in datatype:object_list[index][k]=int(v) if v else None
         if datatype in ["numeric"]:object_list[index][k]=round(float(v),3) if v else None
         if "time" in datatype:object_list[index][k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
         if datatype in ["date"]:object_list[index][k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
         if datatype in ["jsonb"]:object_list[index][k]=json.dumps(v) if v else None
         if datatype in ["ARRAY"]:object_list[index][k]=v.split(",") if v else None
   return {"status":1,"message":object_list}

async def ownership_check(postgres_client,user_id,table,id):
   if table=="users":
      if user_id!=int(id):return {"status":0,"message":"object ownership issue"}
   if table!="users":
      query=f"select created_by_id from {table} where id=:id;"
      query_param={"id":int(id)}
      output=await postgres_client.fetch_all(query=query,values=query_param)
      if not output:return {"status":0,"message":"no object"}
      if user_id!=output[0]["created_by_id"]:return {"status":0,"message":"object ownership issue"}
   return {"status":1,"message":"done"}

import jwt,json
async def auth_check(request,secret_key_root,secret_key_jwt,admin_data):
   user=None
   token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
   api=request.url.path
   gate=api.split("/")[1]
   if gate not in ["","docs","openapi.json","redoc","root","auth","my","public","private","admin"]:return {"status":0,"message":"gate not allowed"}
   if gate=="root" and token!=secret_key_root:return {"status":0,"message":"token root mismatch"}
   if gate in ["my","private","admin"]:user=json.loads(jwt.decode(token,secret_key_jwt,algorithms="HS256")["data"])
   if gate in ["admin"]:
      if False:
         output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":user["id"]})
         user=output[0] if output else None
         if not user:return {"status":0,"message":"no user"}
         user_api_access=user["api_access"]
      if True:user_api_access=admin_data.get(user["id"],None)
      if user_api_access in [None,""," "]:return {"status":0,"message":"user not admin"}
      if api not in user_api_access.split(","):return {"status":0,"message":"api access denied"}
   return {"status":1,"message":user}

import jwt,json
async def create_token(user,secret_key_jwt):
   data=json.dumps({"id":user["id"],"is_active":user["is_active"],"type":user["type"],"is_protected":user["is_protected"]},default=str)
   token=jwt.encode({"exp":time.time()+1000000000000,"data":data},secret_key_jwt)
   return {"status":1,"message":token}

object_list_log=[]
async def create_api_log(postgres_client,user,request,response,response_time_ms):
   global object_list_log
   object={"created_by_id":user["id"] if user else None,"api":request.url.path,"status_code":response.status_code,"response_time_ms":response_time_ms}
   object_list_log.append(object)
   if len(object_list_log)>=3:
      query="insert into log_api (created_by_id,api,status_code,response_time_ms) values (:created_by_id,:api,:status_code,:response_time_ms)"
      await postgres_client.execute_many(query=query,values=object_list_log)
      object_list_log=[]
   return None

async def postgres_add_action_count(postgres_client,action_table,object_table,object_list):
   if not object_list:return {"status":1,"message":object_list}
   key_name=f"{action_table}_count"
   object_list=[dict(item)|{key_name:0} for item in object_list]
   parent_ids_list=[str(item["id"]) for item in object_list if item["id"]]
   parent_ids_string=",".join(parent_ids_list)
   if parent_ids_string:
      query=f"select parent_id,count(*) from {action_table} where parent_table=:parent_table and parent_id in ({parent_ids_string}) group by parent_id;"
      query_param={"parent_table":object_table}
      object_list_action=await postgres_client.fetch_all(query=query,values=query_param)
      for x in object_list:
         for y in object_list_action:
               if x["id"]==y["parent_id"]:
                  x[key_name]=y["count"]
                  break
   return {"status":1,"message":object_list}

async def postgres_add_creator_data(postgres_client,object_list):
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

async def postgres_cud(postgres_client,mode,table,object_list):
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

async def postgres_schema_init(postgres_client,config):
   #extension
   for extension in config["extension"]:
      await postgres_client.execute(f"create extension if not exists {extension}",values={})
   #table
   postgres_schema={}
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   for table in config["table"]:
      if table not in postgres_schema:
         await postgres_client.execute(f"create table if not exists {table} (id bigint primary key generated always as identity not null);", values={})
   #column
   postgres_schema={}
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   for k,v in config["column"].items():
      for table in v[1]:
         if not postgres_schema.get(table,{}).get(k,None):
            await postgres_client.execute(f"alter table {table} add column if not exists {k} {v[0]};", values={})
   #not null
   postgres_schema={}
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   for k,v in config["not_null"].items():
      for table in v:
         if postgres_schema.get(table,{}).get(k,{}).get("nullable")=="YES":
            await postgres_client.execute(f"alter table {table} alter column {k} set not null;", values={})
   #unique
   constraint_name_list=[item["constraint_name"] for item in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))]
   for k,v in config["unique"].items():
      for table in v:
         constraint_name=f"constraint_unique_{table}_{k}" if len(k.split(",")) == 1 else f"constraint_unique_{table}_{''.join([item[0] for item in k.split(',')])}"
         if constraint_name not in constraint_name_list:
            await postgres_client.execute(f"alter table {table} add constraint {constraint_name} unique ({k});",values={})
   #bulk delete disable
   await postgres_client.execute(query="create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;",values={})
   for k,v in config["bulk_delete_disable"].items():
      await postgres_client.execute(query=f"create or replace trigger trigger_delete_disable_bulk_{k} after delete on {k} referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk({v});",values={})
   #index
   index_name_list=[item["indexname"] for item in (await postgres_client.fetch_all(query="select indexname from pg_indexes where schemaname='public';",values={}))]
   for k,v in config["index"].items():
      for table in v[1]:
         index_name=f"index_{table}_{k}"
         if index_name not in index_name_list:
            await postgres_client.execute(query=f"create index concurrently if not exists {index_name} on {table} using {v[0]} ({k});",values={})
   #query
   constraint_name_list=[item["constraint_name"] for item in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))]
   for k,v in config["query"].items():
      if "add constraint" in v and v.split()[5] in constraint_name_list:continue
      await postgres_client.fetch_all(query=v,values={})
   #created_at now (auto)
   postgres_schema={}
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   for table,v in postgres_schema.items():
      if postgres_schema.get(table,{}).get("created_at",{}).get("default","absent")==None:
         await postgres_client.execute(query=f"alter table only {table} alter column created_at set default now();", values={})
   #updated_at now (auto)
   postgres_schema={}
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   await postgres_client.execute(query="create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';",values={})
   for table,v in postgres_schema.items():
      if postgres_schema.get(table,{}).get("updated_at",None):
         await postgres_client.execute(query=f"create or replace trigger trigger_set_updated_at_now_{table} before update on {table} for each row execute procedure function_set_updated_at_now();", values={})
   #is_protected (auto)
   postgres_schema={}
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   for table,v in postgres_schema.items():
      if postgres_schema.get(table,{}).get("is_protected",None):
         await postgres_client.execute(query=f"create or replace rule rule_protect_{table} as on delete to {table} where old.is_protected=1 do instead nothing;", values={})
   #refresh mat all
   query="DO $$ DECLARE r RECORD; BEGIN FOR r IN (select oid::regclass::text as mat_name from pg_class where relkind='m') LOOP EXECUTE 'refresh materialized view ' || quote_ident(r.mat_name); END LOOP; END $$;"
   await postgres_client.execute(query=query,values={})
   #final
   return {"status":1,"message":"done"}

#globals
postgres_client=None
from databases import Database
async def set_postgres_client():
   global postgres_client
   postgres_client=Database(os.getenv("postgres_database_url"),min_size=1,max_size=100)
   await postgres_client.connect()
   return None

postgres_schema={}
postgres_column_datatype={}
async def set_postgres_schema():
   global postgres_schema
   global postgres_column_datatype
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return None

project_data={}
async def set_project_data():
   global project_data
   if "project" in postgres_schema:
      output=await postgres_client.fetch_all(query="select * from project limit 1000",values={})
      for item in output:project_data[item["type"]]=item["description"]
   return None

admin_data={}
async def set_admin_data():
   global admin_data
   if postgres_schema.get("users",{}).get("api_access",None):
      output=await postgres_client.fetch_all(query="select id,api_access from users where api_access is not null limit 10000",values={})
      for item in output:admin_data[item["id"]]=item["api_access"]
   return None

redis_client=None
redis_pubsub=None
import redis.asyncio as redis
async def set_redis_client():
   global redis_client
   global redis_pubsub
   if not redis_client:
      redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(os.getenv("redis_server_url")))
      redis_pubsub=redis_client.pubsub()
      await redis_pubsub.subscribe("postgres_cud")
   return None

rabbitmq_client=None
rabbitmq_channel=None
import pika
async def set_rabbitmq_client():
   global rabbitmq_client
   global rabbitmq_channel
   if not rabbitmq_client:
      rabbitmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("rabbitmq_server_url")))
      rabbitmq_channel=rabbitmq_client.channel()
      rabbitmq_channel.queue_declare(queue="postgres_cud")
   return None

lavinmq_client=None
lavinmq_channel=None
import pika
async def set_lavinmq_client():
   global lavinmq_client
   global lavinmq_channel
   if not lavinmq_client:
      lavinmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("lavinmq_server_url")))
      lavinmq_channel=lavinmq_client.channel()
      lavinmq_channel.queue_declare(queue="postgres_cud")
   return None

kafka_producer_client=None
kafka_consumer_client=None
from aiokafka import AIOKafkaProducer
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def set_kafka_client():
   global kafka_producer_client
   global kafka_consumer_client
   context=create_ssl_context(cafile=os.getenv("kafka_path_cafile"),certfile=os.getenv("kafka_path_certfile"),keyfile=os.getenv("kafka_path_keyfile"))
   kafka_producer_client=AIOKafkaProducer(bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context)
   kafka_consumer_client=AIOKafkaConsumer("postgres_cud",bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
   await kafka_producer_client.start()
   await kafka_consumer_client.start()
   return None

s3_client=None
s3_resource=None
import boto3
if os.getenv("aws_access_key_id"):
   s3_client=boto3.client("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))
   s3_resource=boto3.resource("s3",aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))

sns_client=None
import boto3
if os.getenv("aws_sns_region_name"):sns_client=boto3.client("sns",region_name=os.getenv("aws_sns_region_name"),aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))

ses_client=None
import boto3
if os.getenv("aws_ses_region_name"):ses_client=boto3.client("ses",region_name=os.getenv("aws_ses_region_name"),aws_access_key_id=os.getenv("aws_access_key_id"),aws_secret_access_key=os.getenv("aws_secret_access_key"))

mongodb_client=None
import motor.motor_asyncio
if os.getenv("mongodb_cluster_url"):mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(os.getenv("mongodb_cluster_url"))

import google.generativeai as genai
if os.getenv("secret_key_gemini"):genai.configure(api_key=os.getenv("secret_key_gemini"))

postgres_config_default={
"extension":["postgis"],
"table":["users","post","message","helpdesk","otp","action_like","action_bookmark","action_report","action_block","action_rating","action_comment","action_follow","log_api","log_password","atom","human","feed","project"],
"column":{
"created_at":["timestamptz",["users","post","message","helpdesk","otp","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment","log_api","log_password","atom","human"]],
"created_by_id":["bigint",["users","post","message","helpdesk","otp","action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment","log_api","log_password","atom","human"]],
"updated_at":["timestamptz",["users","post","message","helpdesk","action_report","action_comment","atom","human"]],
"updated_by_id":["bigint",["users","post","message","helpdesk","action_report","action_comment","atom","human"]],
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
"response_time_ms":["numeric(10,3)",["log_api"]],
"type":["text",["users","post","helpdesk","atom","human","feed","project"]],
"title":["text",["users","post","atom","feed","project"]],
"description":["text",["users","post","action_comment","message","helpdesk","atom","human","feed","project"]],
"file_url":["text",["post","action_comment","atom","feed","project"]],
"link_url":["text",["post","atom","human","feed","project"]],
"tag":["text",["users","post","atom","human","feed","project"]],
"status":["text",["action_report","helpdesk","atom","human"]],
"remark":["text",["action_report","helpdesk","atom","human"]],
"rating":["numeric(3,3)",["post","action_rating","human"]],
"metadata":["jsonb",["users","post","atom"]],
"username":["text",["users"]],
"password":["text",["users","log_password"]],
"google_id":["text",["users"]],
"profile_pic_url":["text",["users"]],
"last_active_at":["timestamptz",["users"]],
"api_access":["text",["users"]],
"name":["text",["users","human"]],
"email":["text",["users","post","otp","helpdesk","human"]],
"mobile":["text",["users","post","otp","helpdesk","human"]],
"whatsapp":["text",["users","post","otp","helpdesk","human"]],
"country":["text",["users","human"]],
"state":["text",["users","human"]],
"city":["text",["users","human"]],
"date_of_birth":["date",["users"]],
"year_of_birth":["smallint",["human"]],
"gender":["text",["users","human"]],
"tag_array":["text[]",[]],
"number":["numeric",["atom"]],
"interest":["text",["users","human"]],
"skill":["text",["users","human"]],
"experience":["numeric(10,1)",["human"]],
"college":["text",["human"]],
"education":["text",["human"]],
"linkedin_url":["text",["human"]],
"github_url":["text",["human"]],
"website_url":["text",["human"]],
"resume_url":["text",["human"]],
"salary":["text",["human"]],
"work_type":["text",["human"]],
"work_profile":["text",["human"]],
"company_past":["text",["human"]],
"company_current":["text",["human"]],
"achievement":["text",["human"]],
},
"not_null":{"created_by_id":["message"],"user_id":["message"],"parent_table":["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"],"parent_id":["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]},
"unique":{"username":["users"],"created_by_id,parent_table,parent_id":["action_like","action_bookmark","action_report","action_block","action_follow"]},
"bulk_delete_disable":{"users":1},
"index":{
"created_at":["brin",["users","post"]],
"created_by_id":["btree",["users","post","message","helpdesk","otp","action_rating","action_comment","log_api"]],
"is_active":["btree",["users","post","action_comment"]],
"is_verified":["btree",["users","post","action_comment"]],
"is_read":["btree",["message"]],
"user_id":["btree",["message"]],
"parent_table":["btree",["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]],
"parent_id":["btree",["action_like","action_bookmark","action_report","action_block","action_follow","action_rating","action_comment"]],
"type":["btree",["users","post","helpdesk","atom","human","feed","project"]],
"status":["btree",["action_report","helpdesk"]],
"email":["btree",["users","otp"]],
"mobile":["btree",["users","otp"]],
"password":["btree",["users"]],
"location":["gist",["users","post"]],
"tag":["btree",["users","post","atom"]],
"rating":["btree",["post","action_rating"]],
"tag_array":["gin",[]]
},
"query":{
"root_user_create":f"insert into users (created_at,username,password) values ('2025-01-01','atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3') on conflict do nothing;",
"root_user_disable":"create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"delete_user_procedure_delete":"drop procedure if exists procedure_delete_user",
"delete_user_procedure_create":"create or replace procedure procedure_delete_user(a int) language plpgsql as $$ begin delete from users where id=a;delete from post where created_by_id=a;delete from message where created_by_id=a;delete from message where user_id=a;delete from action_like where created_by_id=a;delete from action_bookmark where created_by_id=a;delete from action_report where created_by_id=a;delete from action_block where created_by_id=a;delete from action_follow where created_by_id=a;delete from action_rating where created_by_id=a;delete from action_comment where created_by_id=a;delete from action_report where parent_table='users' and parent_id=a;delete from action_block where parent_table='users' and parent_id=a;delete from action_follow where parent_table='users' and parent_id=a;delete from action_rating where parent_table='users' and parent_id=a;commit;end;$$;",
"log_password_function":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(created_by_id, user_id, password) VALUES(NEW.updated_by_id, OLD.id, OLD.password); END IF; RETURN NEW; END; $$;",
"log_password_trigger":"CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"view_schema":"create or replace view view_schema as (with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public') select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name);",
"mat_table_row_count":"create materialized view if not exists mat_table_row_count as (select table_name,(xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count from (select table_name, table_schema, query_to_xml(format('select count(*) as cnt from %I.%I', table_schema, table_name), false, true, '') as xml_count from information_schema.tables where table_schema='public'));",
}
}

#helper

async def login_user_check(request,user):
   query_param=dict(request.query_params)
   if "is_exist" in query_param and query_param["is_exist"]=="1" and not user:return {"status":0,"message":"no user"}
   if "type" in query_param and query_param["type"]!=user["type"]:return {"status":0,"message":"user type mismatch"}
   if "is_admin" in query_param and query_param["is_admin"]=="1" and user["api_access"] in [None,""," "]:return {"status":0,"message":"user not admin"}
   return {"status":1,"message":"done"}



async def queue_push(queue,queue_name,data):
   if queue=="redis":output=await redis_client.publish(queue_name,json.dumps(data))
   if queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=queue_name,body=json.dumps(data))
   if queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=queue_name,body=json.dumps(data))
   if queue=="kafka":output=await kafka_producer_client.send_and_wait(queue_name,json.dumps(data,indent=2).encode('utf-8'),partition=0)
   return {"status":1,"message":output}

async def queue_pull_postgres_cud(data):
   try:
      mode,table,object,is_serialize=data["mode"],data["table"],data["object"],data["is_serialize"]
      if is_serialize:
         response=await object_serialize(postgres_column_datatype,[object])
         if response["status"]==0:print(response)
         object=response["message"][0]
      response=await postgres_cud(postgres_client,mode,table,[object])
      if response["status"]==0:print(response)
      print(mode,table,response)
   except Exception:pass
   return None

import asyncio
def aqmp_callback(ch,method,properties,body):
   data=json.loads(body)
   loop=asyncio.get_event_loop()
   loop.run_until_complete(queue_pull_postgres_cud(data))
   return None



#app
import sentry_sdk
sentry_dsn=os.getenv("sentry_dsn")
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_limiter import FastAPILimiter
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
@asynccontextmanager
async def lifespan(app:FastAPI):
   await set_postgres_client()
   await set_postgres_schema()
   await set_project_data()
   await set_admin_data()
   await set_redis_client()
   if os.getenv("rabbitmq_server_url"):await set_rabbitmq_client()
   if os.getenv("lavinmq_server_url"):await set_lavinmq_client()
   if os.getenv("kafka_server_url"):await set_kafka_client()
   await FastAPILimiter.init(redis_client)
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   yield
   if postgres_client:await postgres_client.disconnect()
   if redis_client:await redis_client.aclose()
   if rabbitmq_channel:rabbitmq_channel.close()
   if rabbitmq_client:rabbitmq_client.close()
   if lavinmq_channel:lavinmq_channel.close()
   if lavinmq_client:lavinmq_client.close()
   if kafka_producer_client:await kafka_producer_client.stop()

from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

from fastapi import Request,responses
import time,traceback
from starlette.background import BackgroundTask
@app.middleware("http")
async def middleware(request:Request,api_function):
   try:
      start=time.time()
      response=await auth_check(request,os.getenv("secret_key_root"),os.getenv("secret_key_jwt"),admin_data)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      user=response["message"]
      request.state.user=user
      query_param=dict(request.query_params)
      if request.method!="GET" and "is_background" in query_param and int(query_param["is_background"])==1:
         body=await request.body()
         async def receive():return {"type":"http.request","body":body}
         async def api_function_new():
            reques_new=Request(scope=request.scope,receive=receive)
            await api_function(reques_new)
         task=BackgroundTask(api_function_new)
         response=responses.JSONResponse(status_code=200,content={"status":1,"message":"done"})
         response.background=task
      else:
         response=await api_function(request)
         end=time.time()
         response_time_ms=(end-start)*1000
         if "log_api" in postgres_schema:
            task=BackgroundTask(create_api_log,postgres_client,user,request,response,response_time_ms)
            response.background=task
   except Exception as e:
      print(traceback.format_exc())
      return responses.JSONResponse(status_code=400,content={"status":0,"message":str(e.args)})
   return response

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
from fastapi import Request,UploadFile,responses,Depends,BackgroundTasks,WebSocket,WebSocketDisconnect
import hashlib,datetime,json,uuid,time,jwt,csv,codecs,copy,requests,os,random,sys
from io import BytesIO
from typing import Literal
from bson.objectid import ObjectId
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel

@app.get("/")
async def root(request:Request):
   if project_data.get("index_html",None):response=responses.HTMLResponse(content=project_data["index_html"],status_code=200)
   else:response={"status":1,"message":"welcome to atom"}
   return response

@app.post("/root/postgres-schema-init")
async def root_postgres_schema_init(request:Request,mode:str):
   if mode=="default":config=postgres_config_default
   if mode=="self":config=await request.json()
   await postgres_schema_init(postgres_client,config)
   return {"status":1,"message":"done"}

@app.put("/root/grant-api-access-all")
async def root_grant_api_access_all(request:Request,user_id:int):
   #logic
   api_list=[route.path for route in request.app.routes]
   api_list_admin=[item for item in api_list if "/admin" in item]
   query="update users set api_access=:api_access where id=:id returning *"
   query_param={"api_access":",".join(api_list_admin),"id":user_id}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.delete("/root/postgres-clean")
async def root_pclean(request:Request):
   #creator null
   for item in postgres_schema:
      if item["column_name"]=="created_by_id":
         query=f"delete from {item['table_name']} where created_by_id not in (select id from users);"
         await postgres_client.execute(query=query,values={})
   #action parent null
   for item in postgres_schema:
      if "action_" in item["table_name"] and item ["column_name"]=="parent_table":
         query=f"select distinct(parent_table) from {item['table_name']};"
         output=await postgres_client.fetch_all(query=query,values={})
         for parent_table in output:
            query=f"delete from {item['table_name']} where parent_table='{parent_table['parent_table']}' and parent_id not in (select id from {parent_table['parent_table']});"
            await postgres_client.execute(query=query,values={})      
   #final
   return {"status":1,"message":"done"}

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

@app.put("/root/reset-global")
async def root_reset_global(request:Request):
   await set_postgres_schema()
   await set_project_data()
   await set_admin_data()
   return {"status":1,"message":"done"}

@app.get("/root/variable-size")
async def root_variable_size(request:Request):
   output={}
   globals_dict=globals()
   user_defined_variables={name:value for name,value in globals_dict.items() if not name.startswith("__")}
   for name,var in user_defined_variables.items():output[f"{name} ({type(var).__name__})"]=sys.getsizeof(var)/1024
   output=dict(sorted(output.items(), key=lambda item: item[1],reverse=True))
   return {"status":1,"message":output}

@app.get("/root/ai-prompt")
async def root_ai_prompt(request:Request,ai:str,model:str,prompt:str):
   if ai=="google":
      model=genai.GenerativeModel(model)
      output=model.generate_content(prompt)
      output=output.text
   return {"status":1,"message":output}

@app.post("/auth/signup",dependencies=[Depends(RateLimiter(times=1,seconds=1))])
async def auth_signup(request:Request,username:str,password:str):
   #create user
   query="insert into users (username,password) values (:username,:password) returning *;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=user=output[0]
   #create token
   response=await create_token(user,os.getenv("secret_key_jwt"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
   #final
   return {"status":1,"message":token}

@app.get("/auth/login")
async def auth_login(request:Request,username:str,password:str):
   #read user
   query=f"select * from users where username=:username and password=:password order by id desc limit 1;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   #login user check
   response=await login_user_check(request,user)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #user not exist
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create token
   response=await create_token(user,os.getenv("secret_key_jwt"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
   #final
   return {"status":1,"message":token}

@app.get("/auth/login-google")
async def auth_login_google(request:Request,google_id:str):
   #read user
   query=f"select * from users where google_id=:google_id order by id desc limit 1;"
   query_param={"google_id":hashlib.sha256(google_id.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   #login user check
   response=await login_user_check(request,user)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
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
   response=await create_token(user,os.getenv("secret_key_jwt"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
   #final
   return {"status":1,"message":token}

@app.get("/auth/login-email-otp")
async def auth_login_email_otp(request:Request,email:str,otp:int):
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
   #login user check
   response=await login_user_check(request,user)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
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
   response=await create_token(user,os.getenv("secret_key_jwt"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
   #final
   return {"status":1,"message":token}

@app.get("/auth/login-mobile-otp")
async def auth_login_mobile_otp(request:Request,mobile:str,otp:int):
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
   #login user check
   response=await login_user_check(request,user)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
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
   response=await create_token(user,os.getenv("secret_key_jwt"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
   #final
   return {"status":1,"message":token}

@app.get("/auth/login-email-password")
async def auth_login_email_password(request:Request,email:str,password:str):
   #read user
   query=f"select * from users where email=:email and password=:password order by id desc limit 1;"
   query_param={"email":email,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   #login user check
   response=await login_user_check(request,user)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #user not exist
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create token
   response=await create_token(user,os.getenv("secret_key_jwt"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
   #final
   return {"status":1,"message":token}

@app.get("/auth/login-mobile-password")
async def auth_login_mobile_password(request:Request,mobile:str,password:str):
   #read user
   query=f"select * from users where mobile=:mobile and password=:password order by id desc limit 1;"
   query_param={"mobile":mobile,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   user=output[0] if output else None
   #login user check
   response=await login_user_check(request,user)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #user not exist
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   #create token
   response=await create_token(user,os.getenv("secret_key_jwt"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   token=response["message"]
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
   response=await create_token(user,os.getenv("secret_key_jwt"))
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
   else:output=await queue_push(queue,"postgres_cud",{"mode":"create","table":table,"object":object,"is_serialize":is_serialize})
   #final
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def admin_object_create(request:Request,table:str,is_serialize:int=1):
   #object set
   object=await request.json()
   if "created_by_id" in postgres_table_column[table]:object["created_by_id"]=request.state.user["id"]
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
   else:output=await queue_push(queue,"postgres_cud",{"mode":"update","table":table,"object":object,"is_serialize":is_serialize})
   #final
   return {"status":1,"message":output}

@app.delete("/my/object-delete")
async def my_object_delete(request:Request,table:str,id:int,queue:str=None):
   #check
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   #ownwership check
   response=await ownership_check(postgres_client,request.state.user["id"],table,object["id"])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   #logic
   if not queue:
      query=f"delete from {table} where id=:id and created_by_id=:created_by_id;"
      query_param={"id":id,"created_by_id":request.state.user["id"]}
      output=await postgres_client.execute(query=query,values=query_param)
   else:output=await queue_push(queue,"postgres_cud",{"mode":"delete","table":table,"object":{"id":id},"is_serialize":0})
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
async def my_message_create(request:Request,user_id:int,description:str):
   #delete ids
   query=f"insert into message (created_by_id,user_id,description) values (:created_by_id,:user_id,:description) returning *;"
   query_param={"created_by_id":request.state.user["id"],"user_id":user_id,"description":description}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
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
   #logic
   query="delete from message where id=:id and (created_by_id=:created_by_id or user_id=:user_id);;"
   query_param={"id":id,"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.delete("/my/message-delete-created")
async def my_message_delete_created(request:Request):
   #logic
   query="delete from message where created_by_id=:created_by_id;"
   query_param={"created_by_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.delete("/my/message-delete-received")
async def my_message_delete_received(request:Request):
   #logic
   query="delete from message where user_id=:user_id;"
   query_param={"user_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.delete("/my/message-delete-all")
async def my_message_delete_all(request:Request):
   #logic
   query="delete from message where (created_by_id=:created_by_id or user_id=:user_id);"
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

@app.post("/my/action-create")
async def my_action_create(request:Request,action:str,parent_table:str,parent_id:int):
   #logic
   query_param=dict(request.query_params)
   query_param["created_by_id"]=request.state.user["id"]
   object={k:v for k,v in query_param.items() if k in postgres_column_datatype}
   response=await object_serialize(postgres_column_datatype,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   object=response["message"][0]
   response=await postgres_cud(postgres_client,"create",action,[object])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

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

@app.delete("/my/action-delete-parent")
async def my_action_delete_parent(request:Request,action:str,parent_table:str,parent_id:int):
   #logic
   query=f"delete from {action} where created_by_id=:created_by_id and parent_table=:parent_table and parent_id=:parent_id;"
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id}
   output=await postgres_client.execute(query=query,values=query_param)
   #final
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

@app.get("/public/api-list")
async def public_api_list(request:Request,mode:str=None):
   #logic
   api_list=[route.path for route in request.app.routes]
   api_list_admin=[item for item in api_list if "/admin" in item]
   if not mode:output=api_list
   else:output=api_list_admin
   return {"status":1,"message":output}

@app.get("/public/project-meta")
@cache(expire=60)
async def public_project_meta(request:Request):
   #logic
   query_dict={
   "user_count":"select count(*) from users;"
   }
   temp={k:await postgres_client.fetch_all(query=v,values={}) for k,v in query_dict.items()}
   response={"status":1,"message":temp}
   #final
   return response

@app.get("/public/table-column")
async def public_table_column(request:Request,is_main_column:int=None,table:str=None):
   #logic
   temp={}
   for k in postgres_table_column:temp[k]={}
   for item in postgres_schema:temp[item["table_name"]][item["column_name"]]=item["data_type"]
   #if is_main_column
   temp2=copy.deepcopy(temp)
   if is_main_column==1:
      for k1,v1 in temp2.items():
         for k2,v2 in v1.items():
            if k2 in ['id','created_at','created_by_id','updated_at','updated_by_id','is_active','is_verified','is_protected','last_active_at']:del temp[k1][k2]
   #if table
   if table:temp=temp[table]
   #final
   return {"status":1,"message":temp}

@app.get("/public/verify-otp-email")
async def public_verify_otp_email(request:Request,otp:int,email:str):
   #logic
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
   query_param={"email":email}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #final
   return {"status":1,"message":"done"}

@app.get("/public/verify-otp-mobile")
async def public_verify_otp_mobile(request:Request,otp:int,mobile:str):
   #logic
   query="select * from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
   query_param={"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp not found"})
   if int(output[0]["otp"])!=int(otp):return responses.JSONResponse(status_code=400,content={"status":0,"message":"otp mismatch"})
   #final
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
async def public_object_read(request:Request,table:Literal["users","post","atom","feed"],order:str="id desc",limit:int=100,page:int=1,is_creator_data:int=0,is_action_count:int=0):
   #create where string
   query_param=dict(request.query_params)
   response=await create_where_string(postgres_column_datatype,query_param)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_value=response["message"][0]
   #read object
   if is_creator_data==0:query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   else:query=f'''
   with
   x as (select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit})
   select x.*,u.username as created_by_id_username from x left join users as u on x.created_by_id=u.id order by x.id desc;
   '''
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   #action count
   if is_action_count:
      response=await postgres_add_action_count(postgres_client,"action_like",table,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
      response=await postgres_add_action_count(postgres_client,"action_bookmark",table,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
      response=await postgres_add_action_count(postgres_client,"action_comment",table,object_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object_list=response["message"]
   #final
   return {"status":1,"message":object_list}

@app.get("/public/search-location")
async def public_location_search(request:Request,table:Literal["users","post","atom"],location:str,within:str,order:str="id desc",limit:int=100,page:int=1):
   #start
   long,lat=float(location.split(",")[0]),float(location.split(",")[1])
   min_meter,max_meter=int(within.split(",")[0]),int(within.split(",")[1])
   #create where string
   object_where=dict(request.query_params)
   response=await create_where_string(postgres_column_datatype,object_where)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   #serialize
   response=await object_serialize(postgres_column_datatype,[where_value])
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

class schema_update_api_access(BaseModel):
   user_id:int
   api_access:str|None=None
@app.put("/admin/update-api-access")
async def admin_update_api_access(request:Request,body:schema_update_api_access):
   api_list=[route.path for route in request.app.routes]
   api_list_admin=[item for item in api_list if "/admin" in item]
   #check api access string
   if body.api_access:
      for item in body.api_access.split(","):
         if item not in api_list_admin:return responses.JSONResponse(status_code=400,content={"status":0,"message":"wrong api access string"})
   #api_access key
   if not body.api_access:api_access=None
   elif len(body.api_access)<=5:api_access=None
   else:api_access=body.api_access
   #logic
   query="update users set api_access=:api_access where id=:id returning *"
   query_param={"id":body.user_id,"api_access":api_access}
   output=await postgres_client.execute(query=query,values=query_param)
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
   if "updated_by_id" in postgres_table_column[table]:object["updated_by_id"]=request.state.user["id"]
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
  #stop keywords
  for item in ["insert","update","delete","alter","drop"]:
    if item in query:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{item} not allowed in query"})
  #query run
  output=await postgres_client.fetch_all(query=query,values={})
  #final
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

@app.get("/root/redis-info")
async def root_redis_info(request:Request):
   output=await redis_client.info()
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

#main
import sys
import asyncio
import json
mode=sys.argv

import uvicorn
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_redis_client()
   try:
      async for message in redis_pubsub.listen():
         if message["type"]=="message" and message["channel"]==b'postgres_cud':
            data=json.loads(message['data'])
            await queue_pull_postgres_cud(data)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await redis_pubsub.unsubscribe("postgres_cud")
      await redis_client.aclose()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="redis":
    try:asyncio.run(main_redis())
    except KeyboardInterrupt:print("exit")
    
async def main_rabbitmq():
   await set_postgres_client()
   await set_postgres_schema()
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
   await set_postgres_client()
   await set_postgres_schema()
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
   
async def main_kafka():
   await set_postgres_client()
   await set_postgres_schema()
   await set_kafka_client()
   try:
      async for message in kafka_consumer_client:
         if message.topic=="postgres_cud":
            data=json.loads(message.value.decode('utf-8'))
            await queue_pull_postgres_cud(data)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await kafka_consumer_client.stop()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="kafka":
    try:asyncio.run(main_kafka())
    except KeyboardInterrupt:print("exit")

