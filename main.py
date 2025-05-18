#function
import httpx
async def send_email_resend(resend_key,resend_url,sender_email,email_list,title,body):
   payload={"from":sender_email,"to":email_list,"subject":title,"html":body}
   headers={"Authorization":f"Bearer {resend_key}","Content-Type": "application/json"}
   async with httpx.AsyncClient() as client:output=await client.post(resend_url,json=payload,headers=headers)
   if output.status_code==200:response={"status":1,"message":"done"}
   else:response={"status":0,"message":f"Resend error:{response.text}"}
   return response

import gspread
from google.oauth2.service_account import Credentials
async def gsheet_client_read(gsheet_service_account_json_path,gsheet_scope_list):
   gsheet_client=gspread.authorize(Credentials.from_service_account_file(gsheet_service_account_json_path,scopes=gsheet_scope_list))
   return gsheet_client

async def gsheet_create(gsheet_client,spreadsheet_id,sheet_name,object):
   row=[object[key] for key in sorted(object.keys())]
   output=gsheet_client.open_by_key(spreadsheet_id).worksheet(sheet_name).append_row(row)
   return output

async def gsheet_read_service_account(gsheet_client,spreadsheet_id,sheet_name,cell_boundary):
   worksheet=gsheet_client.open_by_key(spreadsheet_id).worksheet(sheet_name)
   if cell_boundary:output=worksheet.get(cell_boundary)
   else:output=worksheet.get_all_records()
   return output

import pandas
async def gsheet_read_pandas(spreadsheet_id,gid):
   url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
   df=pandas.read_csv(url)
   output=df.to_dict(orient="records")
   return output

async def openai_prompt(openai_client,model,prompt,is_web_search,previous_response_id):
   if not openai_client or not model or not prompt:return {"status":0,"message":"param missing"}
   params={"model":model,"input":prompt}
   if is_web_search==1:params["tools"]=[{"type":"web_search"}]
   if previous_response_id:params["previous_response_id"]=previous_response_id
   output=openai_client.responses.create(**params)
   return {"status":1,"message":output}

import base64
async def openai_ocr(openai_client,model,prompt,file):
   contents=await file.read()
   b64_image=base64.b64encode(contents).decode("utf-8")
   output=openai_client.responses.create(model=model,input=[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":f"data:image/png;base64,{b64_image}"},],}],)
   return output

from databases import Database
async def postgres_client_read(postgres_url):
   postgres_client=Database(postgres_url,min_size=1,max_size=100)
   await postgres_client.connect()
   return postgres_client

import asyncpg
async def postgres_client_asyncpg_read(postgres_url):
   postgres_client_asyncpg=await asyncpg.connect(postgres_url)
   return postgres_client_asyncpg

import redis.asyncio as redis
async def redis_client_read(redis_url):
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_url))
   return redis_client

import redis.asyncio as redis
async def redis_pubsub_read(redis_url,channel_name):
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_url))
   redis_pubsub=redis_client.pubsub()
   await redis_pubsub.subscribe(channel_name)
   return redis_client,redis_pubsub

import motor.motor_asyncio
async def mongodb_client_read(mongodb_url):
   mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
   return mongodb_client

import boto3
async def s3_client_read(s3_region_name,aws_access_key_id,aws_secret_access_key):
   s3_client=boto3.client("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   s3_resource=boto3.resource("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return s3_client,s3_resource

import boto3
async def sns_client_read(sns_region_name,aws_access_key_id,aws_secret_access_key):
   sns_client=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return sns_client

import boto3
async def ses_client_read(ses_region_name,aws_access_key_id,aws_secret_access_key):
   ses_client=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return ses_client

import pika
async def rabbitmq_client_read(rabbitmq_url,channel_name):
   rabbitmq_client=pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
   rabbitmq_channel=rabbitmq_client.channel()
   rabbitmq_channel.queue_declare(queue=channel_name)
   return rabbitmq_client,rabbitmq_channel

import pika
async def lavinmq_client_read(lavinmq_url,channel_name):
   lavinmq_client=pika.BlockingConnection(pika.URLParameters(lavinmq_url))
   lavinmq_channel=lavinmq_client.channel()
   lavinmq_channel.queue_declare(queue=channel_name)
   return lavinmq_client,lavinmq_channel

from aiokafka import AIOKafkaProducer
from aiokafka.helpers import create_ssl_context
async def kafka_producer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name):
   context=create_ssl_context(cafile=kafka_path_cafile,certfile=kafka_path_certfile,keyfile=kafka_path_keyfile)
   kafka_producer_client=AIOKafkaProducer(bootstrap_servers=kafka_url,security_protocol="SSL",ssl_context=context)
   await kafka_producer_client.start()
   return kafka_producer_client

from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def kafka_consumer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name):
   context=create_ssl_context(cafile=kafka_path_cafile,certfile=kafka_path_certfile,keyfile=kafka_path_keyfile)
   kafka_consumer_client=AIOKafkaConsumer(channel_name,bootstrap_servers=kafka_url,security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
   await kafka_consumer_client.start()
   return kafka_consumer_client

async def postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   column_insert_list=list(object_list[0].keys())
   query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_update(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_update_user(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize,user_id):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id and created_by_id={user_id} returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_delete(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   query=f"delete from {table} where id=:id;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_delete_any(table,object,postgres_client,create_where_string,object_serialize,postgres_column_datatype):
   where_string,where_value=await create_where_string(object,object_serialize,postgres_column_datatype)
   query=f"delete from {table} {where_string};"
   await postgres_client.execute(query=query,values=where_value)
   return None

async def postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string):
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   column=object.get("column","*")
   location_filter=object.get("location_filter")
   if location_filter:
      location_filter_split=location_filter.split(",")
      long,lat,min_meter,max_meter=float(location_filter_split[0]),float(location_filter_split[1]),int(location_filter_split[2]),int(location_filter_split[3])
   where_string,where_value=await create_where_string(object,object_serialize,postgres_column_datatype)
   if location_filter:query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
   else:query=f"select {column} from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   return object_list

async def postgres_parent_read(table,parent_column,parent_table,postgres_client,order,limit,offset,user_id):
   query=f'''
   with
   x as (select {parent_column} from {table} where (created_by_id=:created_by_id or :created_by_id is null) order by {order} limit {limit} offset {offset}) 
   select ct.* from x left join {parent_table}  as ct on x.{parent_column}=ct.id;
   '''
   values={"created_by_id":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

import hashlib,datetime,json
async def object_serialize(object_list,postgres_column_datatype):
   for index,object in enumerate(object_list):
      for key,value in object.items():
         datatype=postgres_column_datatype.get(key)
         if not datatype:continue
         if not value:continue
         elif key in ["password"]:object_list[index][key]=hashlib.sha256(str(value).encode()).hexdigest()
         elif datatype=="text" and value in ["","null"]:object_list[index][key]=None
         elif datatype=="text":object_list[index][key]=value.strip()
         elif "int" in datatype:object_list[index][key]=int(value)
         elif datatype=="numeric":object_list[index][key]=round(float(value),3)
         elif datatype=="date":object_list[index][key]=datetime.datetime.strptime(value,'%Y-%m-%d')
         elif "time" in datatype:object_list[index][key]=datetime.datetime.strptime(value,'%Y-%m-%dT%H:%M:%S')
         elif datatype=="ARRAY":object_list[index][key]=value.split(",")
         elif datatype=="jsonb":object_list[index][key]=json.dumps(value)
   return object_list

async def create_where_string(object,object_serialize,postgres_column_datatype):
   object={k:v for k,v in object.items() if (k in postgres_column_datatype and k not in ["metadata","location","table","order","limit","page"] and v is not None)}
   where_operator={k:v.split(',',1)[0] for k,v in object.items()}
   where_value={k:v.split(',',1)[1] for k,v in object.items()}
   object_list=await object_serialize([where_value],postgres_column_datatype)
   where_value=object_list[0]
   where_string_list=[f"({key} {where_operator[key]} :{key} or :{key} is null)" for key in [*object]]
   where_string_joined=' and '.join(where_string_list)
   where_string=f"where {where_string_joined}" if where_string_joined else ""
   return where_string,where_value
   
import random
async def generate_save_otp(postgres_client,email,mobile):
   if email and mobile:return {"status":0,"message":"send either email/mobile"}
   if not email and not mobile:return {"status":0,"message":"send either email/mobile"}
   otp=random.randint(100000,999999)
   if email:await postgres_client.execute(query="insert into otp (otp,email) values (:otp,:email) returning *;",values={"otp":otp,"email":email.strip().lower()})
   if mobile:await postgres_client.execute(query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;",values={"otp":otp,"mobile":mobile.strip().lower()})
   return {"status":1,"message":otp}
   
async def verify_otp(postgres_client,otp,email,mobile):
   if email and mobile:return {"status":0,"message":"send either email/mobile"}
   if not email and not mobile:return {"status":0,"message":"send either email/mobile"}
   if email:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;",values={"email":email})
   if mobile:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;",values={"mobile":mobile})
   if not output:return {"status":0,"message":"otp not found"}
   if int(output[0]["otp"])!=int(otp):return {"status":0,"message":"otp mismatch"}
   return {"status":1,"message":"done"}

async def postgres_schema_read(postgres_client):
   query='''
   WITH t AS (SELECT * FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'),
   c AS (
   SELECT table_name, column_name, data_type, 
   CASE WHEN is_nullable='YES' THEN 1 ELSE 0 END AS is_nullable, 
   column_default 
   FROM information_schema.columns 
   WHERE table_schema='public'
   ), 
   i AS (
   SELECT t.relname::text AS table_name, a.attname AS column_name, 
   CASE WHEN idx.indisprimary OR idx.indisunique OR idx.indisvalid THEN 1 ELSE 0 END AS is_index
   FROM pg_attribute a
   JOIN pg_class t ON a.attrelid=t.oid
   JOIN pg_namespace ns ON t.relnamespace=ns.oid
   LEFT JOIN pg_index idx ON a.attrelid=idx.indrelid AND a.attnum=ANY(idx.indkey)
   WHERE ns.nspname='public' AND a.attnum > 0 AND t.relkind='r'
   )
   SELECT t.table_name as table, c.column_name as column, c.data_type as datatype,c.column_default as default, c.is_nullable as is_null, COALESCE(i.is_index, 0) AS is_index 
   FROM t 
   LEFT JOIN c ON t.table_name=c.table_name 
   LEFT JOIN i ON t.table_name=i.table_name AND c.column_name=i.column_name;
   '''
   output=await postgres_client.fetch_all(query=query,values={})
   postgres_schema={}
   for object in output:
      table,column=object["table"],object["column"]
      column_data={"datatype":object["datatype"],"default":object["default"],"is_null":object["is_null"],"is_index":object["is_index"]}
      if table not in postgres_schema:postgres_schema[table]={}
      postgres_schema[table][column]=column_data
   return postgres_schema

async def postgres_column_datatype_read(postgres_client,postgres_schema_read):
   postgres_schema=await postgres_schema_read(postgres_client)
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return postgres_column_datatype

async def postgres_schema_init(postgres_client,postgres_schema_read,config):
   #extension
   await postgres_client.fetch_all(query="create extension if not exists postgis;",values={})
   await postgres_client.fetch_all(query="create extension if not exists pg_trgm;",values={})
   #table
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column_list in config["table"].items():
      is_table=postgres_schema.get(table,{})
      if not is_table:
         query=f"create table if not exists {table} (id bigint primary key generated always as identity not null);"
         await postgres_client.execute(query=query,values={})
   #column
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column_list in config["table"].items():
      for column in column_list:
         column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
         is_column=postgres_schema.get(table,{}).get(column_name,{})
         if not is_column:
            query=f"alter table {table} add column if not exists {column_name} {column_datatype};"
            await postgres_client.execute(query=query,values={})
   #nullable
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column_list in config["table"].items():
      for column in column_list:
         column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
         is_null=postgres_schema.get(table,{}).get(column_name,{}).get("is_null",None)
         if column_is_mandatory=="0" and is_null==0:
            query=f"alter table {table} alter column {column_name} drop not null;"
            await postgres_client.execute(query=query,values={})
         if column_is_mandatory=="1" and is_null==1:
            query=f"alter table {table} alter column {column_name} set not null;"
            await postgres_client.execute(query=query,values={})
   #index
   postgres_schema=await postgres_schema_read(postgres_client)
   index_name_list=[object["indexname"] for object in (await postgres_client.fetch_all(query="SELECT indexname FROM pg_indexes WHERE schemaname='public';",values={}))]
   for table,column_list in config["table"].items():
      for column in column_list:
         column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
         if column_index_type=="0":
            query=f"DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname ILIKE 'index_{table}_{column_name}_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;"
            await postgres_client.execute(query=query,values={})
         else:
            index_type_list=column_index_type.split(",")
            for index_type in index_type_list:
               index_name=f"index_{table}_{column_name}_{index_type}"
               if index_name not in index_name_list:
                  if index_type=="gin":
                     query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name} gin_trgm_ops);"
                     await postgres_client.execute(query=query,values={})
                  else:
                     query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name});"
                     await postgres_client.execute(query=query,values={})
   #query
   constraint_name_list={object["constraint_name"].lower() for object in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))}
   for query in config["query"].values():
      if query.split()[0]=="0":continue
      if "add constraint" in query.lower() and query.split()[5].lower() in constraint_name_list:continue
      await postgres_client.fetch_all(query=query,values={})
   #final
   return None

async def ownership_check(postgres_client,table,id,user_id):
   if table=="users":
      if id!=user_id:return {"status":0,"message":"object ownership issue"}
   if table!="users":
      output=await postgres_client.fetch_all(query=f"select created_by_id from {table} where id=:id;",values={"id":id})
      if not output:return {"status":0,"message":"no object"}
      if output[0]["created_by_id"]!=user_id:return {"status":0,"message":"object ownership issue"}
   return {"status":1,"message":"done"}

async def add_creator_data(postgres_client,object_list,user_key):
    object_list=[dict(object) for object in object_list]
    created_by_ids={str(object["created_by_id"]) for object in object_list if object.get("created_by_id")}
    users={}
    if created_by_ids:
        query = f"SELECT * FROM users WHERE id IN ({','.join(created_by_ids)});"
        users = {str(user["id"]): dict(user) for user in await postgres_client.fetch_all(query=query,values={})}
    for object in object_list:
        created_by_id = str(object.get("created_by_id"))
        if created_by_id in users:
            for key in user_key.split(","):
                object[f"creator_{key}"] = users[created_by_id].get(key)
        else:
            for key in user_key.split(","):
                object[f"creator_{key}"] = None
    return object_list
 
async def postgres_query_runner(postgres_client,query,user_id):
   danger_word=["drop","truncate"]
   stop_word=["drop","delete","update","insert","alter","truncate","create", "rename","replace","merge","grant","revoke","execute","call","comment","set","disable","enable","lock","unlock"]
   must_word=["select"]
   for item in danger_word:
      if item in query.lower():return {"status":0,"message":f"{item} keyword not allowed in query"}
   if user_id!=1:
      for item in stop_word:
         if item in query.lower():return {"status":0,"message":f"{item} keyword not allowed in query"}
      for item in must_word:
         if item not in query.lower():return {"status":0,"message":f"{item} keyword not allowed in query"}
   output=await postgres_client.fetch_all(query=query,values={})
   return {"status":1,"message":output}

async def postgres_update_ids(postgres_client,table,ids,column,value,updated_by_id,created_by_id):
   query=f"update {table} set {column}=:value,updated_by_id=:updated_by_id where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"value":value,"created_by_id":created_by_id,"updated_by_id":updated_by_id}
   await postgres_client.execute(query=query,values=values)
   return None

async def postgres_delete_ids(postgres_client,table,ids,created_by_id):
   query=f"delete from {table} where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"created_by_id":created_by_id}
   await postgres_client.execute(query=query,values=values)
   return None

import uuid
from io import BytesIO
async def s3_file_upload_direct(s3_client,s3_region_name,bucket,key_list,file_list):
   if not key_list:key_list=[f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}" for file in file_list]
   output={}
   for index,file in enumerate(file_list):
      key=key_list[index]
      if "." not in key:return {"status":0,"message":"extension must"}
      file_content=await file.read()
      file_size_kb=round(len(file_content)/1024)
      if file_size_kb>100:return {"status":0,"message":f"{file.filename} has {file_size_kb} kb size which is not allowed"}
      s3_client.upload_fileobj(BytesIO(file_content),bucket,key)
      output[file.filename]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
      file.file.close()
   return {"status":1,"message":output}

async def s3_file_upload_presigned(s3_client,s3_region_name,bucket,key,expiry_sec,size_kb):
   if "." not in key:return {"status":0,"message":"extension must"}
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec, Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   return {"status":1,"message":output}
     
import csv,io
async def file_to_object_list(file):
   content=await file.read()
   content=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(content))
   object_list=[row for row in reader]
   await file.close()
   return object_list

async def form_data_read(request):
   form_data=await request.form()
   object={key:value for key,value in form_data.items() if isinstance(value,str)}
   file_list=[file for key,value in form_data.items() for file in form_data.getlist(key)  if key not in object and file.filename]
   return object,file_list

import json
async def redis_set_object(redis_client,key,expiry,object):
   object=json.dumps(object)
   if not expiry:output=await redis_client.set(key,object)
   else:output=await redis_client.setex(key,expiry,object)
   return output

import json
async def redis_get_object(redis_client,key):
   output=await redis_client.get(key)
   if output:output=json.loads(output)
   return output

import jwt,json
async def token_decode(token,key_jwt):
   user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
   return user

import jwt,json,time
async def token_create(key_jwt,token_expire_sec,user):
   user={"id":user["id"]}
   user=json.dumps(user,default=str)
   token=jwt.encode({"exp":time.time()+token_expire_sec,"data":user},key_jwt)
   return token

async def read_user_single(postgres_client,user_id):
   output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":user_id})
   user=dict(output[0]) if output else None
   if not user:return {"status":0,"message":"user not found"}
   return {"status":1,"message":user}

async def users_api_access_check(user_id,api_id_value,users_api_access,postgres_client):
   user_api_access=users_api_access.get(user_id,"absent")
   if user_api_access=="absent":
      output=await postgres_client.fetch_all(query="select id,api_access from users where id=:id;",values={"id":user_id})
      user=output[0] if output else None
      if not user:return {"status":0,"message":"user not found"}
      api_access_str=user["api_access"]
      if not api_access_str:return {"status":0,"message":"api access denied"}
      user_api_access=[int(item.strip()) for item in api_access_str.split(",")]
   if api_id_value not in user_api_access:return {"status":0,"message":"api access denied"}
   return {"status":1,"message":"done"}

async def users_is_active_check(user_id,users_is_active,postgres_client):
   user_is_active=users_is_active.get(user_id,"absent")
   if user_is_active=="absent":
      output=await postgres_client.fetch_all(query="select id,is_active from users where id=:id;",values={"id":user_id})
      user=output[0] if output else None
      if not user:return {"status":0,"message":"user not found"}
      user_is_active=user["is_active"]
   if user_is_active==0:return {"status":0,"message":"user not active"}
   return {"status":1,"message":"done"}

async def users_is_active_read(postgres_client_asyncpg,limit):
   users_is_active={}
   async with postgres_client_asyncpg.transaction():
      cursor=await postgres_client_asyncpg.cursor('SELECT id,is_active FROM users ORDER BY id DESC')
      count=0
      while count < limit:
         batch=await cursor.fetch(10000)
         if not batch:break
         users_is_active.update({record['id']: record['is_active'] for record in batch})
         if False:await redis_client.mset({f"users_is_active_{record['id']}":0 if record['is_active']==0 else 1 for record in batch})
         count+=len(batch)
   return users_is_active

async def users_api_access_read(postgres_client_asyncpg,limit):
   users_api_access={}
   async with postgres_client_asyncpg.transaction():
      cursor=await postgres_client_asyncpg.cursor('SELECT id,api_access FROM users where api_access is not null ORDER BY id DESC')
      count=0
      while count < limit:
         batch=await cursor.fetch(10000)
         if not batch:break
         users_api_access.update({record['id']:[int(item.strip()) for item in record["api_access"].split(",")] for record in batch})
         if False:await redis_client.mset({f"users_api_access_{record['id']}":record['api_access'] for record in batch})
         count+=len(batch)
   return users_api_access

from fastapi import Request,responses
from starlette.background import BackgroundTask
async def api_response_background(request,api_function):
   body=await request.body()
   async def receive():return {"type":"http.request","body":body}
   async def api_function_new():
      request_new=Request(scope=request.scope,receive=receive)
      await api_function(request_new)
   response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
   response.background=BackgroundTask(api_function_new)
   return response

import json
object_list_log_api=[]
async def log_api_create(object,batch,postgres_create,postgres_client,postgres_column_datatype,object_serialize):
   global object_list_log_api
   object_list_log_api.append(object)
   if len(object_list_log_api)>=batch:
      await postgres_create("log_api",object_list_log_api,0,postgres_client,postgres_column_datatype,object_serialize)
      object_list_log_api=[]
   return None

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
async def cache_init(redis_client,redis_key_builder):
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   
import os
def router_add(router_list,app):
   for item in router_list:
       router=__import__(item).router
       app.include_router(router)

async def redis_object_create(redis_client,table,object_list,expiry):
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if not expiry:pipe.set(key,json.dumps(object))
         else:pipe.setex(key,expiry,json.dumps(object))
      await pipe.execute()
   return None

async def s3_url_delete(url,s3_resource):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=s3_resource.Object(bucket,key).delete()
   return output

import datetime
async def update_user_last_active_at(postgres_client,user_id):
   query="update users set last_active_at=:last_active_at where id=:id;"
   values={"id":user_id,"last_active_at":datetime.datetime.now()}
   await postgres_client.execute(query=query,values=values)
   return None

async def mongodb_create_object(mongodb_client,database,table,object_list):
   mongodb_client_database=mongodb_client[database]
   output=await mongodb_client_database[table].insert_many(object_list)
   return str(output)

async def message_inbox_user(postgres_client,user_id,order,limit,offset,is_unread):
   if not is_unread:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {offset};'''
   elif int(is_unread)==1:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {offset};'''
   values={"created_by_id":user_id,"user_id":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

async def message_received_user(postgres_client,user_id,order,limit,offset,is_unread):
   if not is_unread:query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {offset};"
   elif int(is_unread)==1:query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {offset};"
   values={"user_id":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

async def message_thread_user(postgres_client,user_id_1,user_id_2,order,limit,offset):
   query=f"select * from message where ((created_by_id=:user_id_1 and user_id=:user_id_2) or (created_by_id=:user_id_2 and user_id=:user_id_1)) order by {order} limit {limit} offset {offset};"
   values={"user_id_1":user_id_1,"user_id_2":user_id_2}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

async def mark_message_read_thread(postgres_client,user_id_1,user_id_2):
   query="update message set is_read=1 where created_by_id=:created_by_id and user_id=:user_id;"
   values={"created_by_id":user_id_2,"user_id":user_id_1}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_single(postgres_client,user_id,message_id):
   query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id,"id":message_id}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_created(postgres_client,user_id):
   query="delete from message where created_by_id=:user_id;"
   values={"user_id":user_id}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_received(postgres_client,user_id):
   query="delete from message where user_id=:user_id;"
   values={"user_id":user_id}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_all(postgres_client,user_id):
   query="delete from message where (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id}
   await postgres_client.execute(query=query,values={})
   return None

async def send_email_ses(ses_client,sender_email,email_list,title,body):
   ses_client.send_email(
   Source=sender_email,
   Destination={"ToAddresses":email_list},
   Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}}
   )
   return None

async def send_message_template_sns(sns_client,mobile,message,entity_id,template_id,sender_id):
   sns_client.publish(
      PhoneNumber=mobile,
      Message=message,
      MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return None

async def s3_bucket_create(s3_client,bucket,s3_region_name):
   output=s3_client.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})
   return output

async def s3_bucket_public(s3_client,bucket):
   s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return output

async def s3_bucket_empty(s3_resource,bucket):
   output=s3_resource.Bucket(bucket).objects.all().delete()
   return output

async def s3_bucket_delete(s3_client,bucket):
   output=s3_client.delete_bucket(Bucket=bucket)
   return output

from google.oauth2 import id_token
from google.auth.transport import requests
def google_user_read(google_token,google_client_id):
   request=requests.Request()
   id_info=id_token.verify_oauth2_token(google_token,request,google_client_id)
   google_user={"sub": id_info.get("sub"),"email": id_info.get("email"),"name": id_info.get("name"),"picture": id_info.get("picture"),"email_verified": id_info.get("email_verified")}
   return google_user

import hashlib
async def signup_username_password(postgres_client,type,username,password):
   query="insert into users (type,username,password) values (:type,:username,:password) returning *;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   return output[0]

async def signup_username_password_bigint(postgres_client,type,username_bigint,password_bigint):
   query="insert into users (type,username_bigint,password_bigint) values (:type,:username_bigint,:password_bigint) returning *;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await postgres_client.fetch_all(query=query,values=values)
   return output[0]

import hashlib
async def login_password_username(postgres_client,token_create,key_jwt,token_expire_sec,type,username,password):
   query=f"select * from users where type=:type and username=:username and password=:password order by id desc limit 1;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return {"status":0,"message":"user not found"}
   token=await token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

import hashlib
async def login_password_username_bigint(postgres_client,token_create,key_jwt,token_expire_sec,type,username_bigint,password_bigint):
   query=f"select * from users where type=:type and username_bigint=:username_bigint and password_bigint=:password_bigint order by id desc limit 1;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return {"status":0,"message":"user not found"}
   token=await token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

import hashlib
async def login_password_email(postgres_client,token_create,key_jwt,token_expire_sec,type,email,password):
   query=f"select * from users where type=:type and email=:email and password=:password order by id desc limit 1;"
   values={"type":type,"email":email,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return {"status":0,"message":"user not found"}
   token=await token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

import hashlib
async def login_password_mobile(postgres_client,token_create,key_jwt,token_expire_sec,type,mobile,password):
   query=f"select * from users where type=:type and mobile=:mobile and password=:password order by id desc limit 1;"
   values={"type":type,"mobile":mobile,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return {"status":0,"message":"user not found"}
   token=await token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

async def login_otp_email(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,email,otp):
   response=await verify_otp(postgres_client,otp,email,None)
   if response["status"]==0:return response
   query=f"select * from users where type=:type and email=:email order by id desc limit 1;"
   values={"type":type,"email":email}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,email) values (:type,:email) returning *;"
      values={"type":type,"email":email}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

async def login_otp_mobile(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,mobile,otp):
   response=await verify_otp(postgres_client,otp,None,mobile)
   if response["status"]==0:return response
   query=f"select * from users where type=:type and mobile=:mobile order by id desc limit 1;"
   values={"type":type,"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,mobile) values (:type,:mobile) returning *;"
      values={"type":type,"mobile":mobile}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

async def login_google(postgres_client,token_create,key_jwt,token_expire_sec,google_user_read,google_client_id,type,google_token):
   google_user=google_user_read(google_token,google_client_id)
   query=f"select * from users where type=:type and google_id=:google_id order by id desc limit 1;"
   values={"type":type,"google_id":google_user["sub"]}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,google_id,google_data) values (:type,:google_id,:google_data) returning *;"
      values={"type":type,"google_id":google_user["sub"],"google_data":json.dumps(google_user)}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

from fastapi import responses
def error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})

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

#config
if os.path.exists("config.py"):import config

#variable
api_id={
"/admin/object-create":1,
"/admin/object-update":2,
"/admin/ids-update":3,
"/admin/ids-delete":4,
"/admin/object-read":5,
"/admin/db-runner":6
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
"atom":[
"type-smallint-0-btree",
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
"type-smallint-1-btree",
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
gsheet_client=None

#openai client
from openai import OpenAI
if openai_key:openai_client=OpenAI(api_key=openai_key)

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
      #users api access
      global users_api_access
      if postgres_schema.get("users"):users_api_access=await users_api_access_read(postgres_client_asyncpg,users_api_access_max_count)
      #users is_active
      global users_is_active
      if postgres_schema.get("users"):users_is_active=await users_is_active_read(postgres_client_asyncpg,users_is_active_max_count)
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
      #cache
      if cache_client=="valkey":await cache_init(valkey_client,redis_key_builder)
      else:await cache_init(redis_client,redis_key_builder)
      #ratelimiter
      if ratelimiter_client=="valkey":await FastAPILimiter.init(valkey_client)
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
   except Exception as e:print(e.args)

#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#sentry
import sentry_sdk
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

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
      request.state.postgres_client=postgres_client
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
      if "admin/" in request.url.path:
         response=await users_api_access_check(request.state.user["id"],api_id[request.url.path],users_api_access,postgres_client)
         if response["status"]==0:return error(response["message"])
      #is_active check
      if is_active_check_api_keyword:
         for item in is_active_check_api_keyword.split(","):
            if item in request.url.path:
               response=await users_is_active_check(request.state.user["id"],users_is_active,postgres_client)
               if response["status"]==0:return error(response["message"])
      #api response
      if request.query_params.get("is_background")=="1":response=await api_response_background(request,api_function)
      else:response=await api_function(request)
      #api log
      object={"created_by_id":request.state.user.get("id",None),"api":request.url.path,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000}
      asyncio.create_task(log_api_create(object,log_api_batch_count,postgres_create,postgres_client,postgres_column_datatype,object_serialize))
   except Exception as e:
      print(traceback.format_exc())
      response=error(str(e.args))
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
   if mode=="1":postgres_config=postgres_schema_default
   elif mode=="2":postgres_config=config.postgres_schema
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
   #logic
   await postgres_client.execute(query="update users set is_active=1,is_deleted=null where id=1;",values={})
   if postgres_schema.get("log_api"):await postgres_client.execute(query="delete from log_api where created_at<now()-interval '30 days';",values={})
   if postgres_schema.get("otp"):await postgres_client.execute(query="delete from otp where created_at<now()-interval '30 days';",values={})
   if postgres_schema.get("message"):await postgres_client.execute(query="delete from message where created_at<now()-interval '30 days';",values={})
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
   response=await login_password_username(postgres_client,token_create,key_jwt,token_expire_sec,type,username,password)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/auth/login-password-username-bigint")
async def auth_login_password_username(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username_bigint=object.get("username_bigint")
   password_bigint=object.get("password_bigint")
   if not type or not username_bigint or not password_bigint:return error("type/username_bigint/password_bigint missing")
   #logic
   response=await login_password_username_bigint(postgres_client,token_create,key_jwt,token_expire_sec,type,username_bigint,password_bigint)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   email=object.get("email")
   password=object.get("password")
   if not type or not email or not password:return error("type/email/password missing")
   #logic
   response=await login_password_email(postgres_client,token_create,key_jwt,token_expire_sec,type,email,password)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   mobile=object.get("mobile")
   password=object.get("password")
   if not type or not mobile or not password:return error("type/mobile/password missing")
   #logic
   response=await login_password_mobile(postgres_client,token_create,key_jwt,token_expire_sec,type,mobile,password)
   if response["status"]==0:return error(response["message"])
   #final
   return response

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
   response=await login_otp_email(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,email,otp)
   if response["status"]==0:return error(response["message"])
   #final
   return response
   
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
   response=await login_otp_mobile(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,mobile,otp)
   if response["status"]==0:return error(response["message"])
   #final
   return response

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
   response=await read_user_single(postgres_client,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   asyncio.create_task(update_user_last_active_at(postgres_client,request.state.user["id"]))
   #final
   return response

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   #read user
   response=await read_user_single(postgres_client,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   user=response["message"]
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
   response=await read_user_single(postgres_client,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   user=response["message"]
   if user["api_access"]:return error("not allowed as you have api_access")
   #logic
   if mode=="soft":await postgres_client.execute(query="update users set is_deleted=1 where id=:id;",values={"id":request.state.user["id"]})
   elif mode=="hard":await postgres_client.execute(query="delete from users where id=:id;",values={"id":request.state.user["id"]})
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
      response=await verify_otp(postgres_client,otp,email,mobile)
      if response["status"]==0:return error(response["message"])
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
      asyncio.create_task(postgres_client.execute(query=f"update message set is_read=1 where id in ({ids});",values={}))
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
   response=await generate_save_otp(postgres_client,None,mobile)
   if response["status"]==0:return error(response["message"])
   otp=response["message"]
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
   response=await generate_save_otp(postgres_client,None,mobile)
   if response["status"]==0:return error(response["message"])
   otp=response["message"]
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
   response=await generate_save_otp(postgres_client,email,None)
   if response["status"]==0:return error(response["message"])
   otp=response["message"]
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
   response=await generate_save_otp(postgres_client,email,None)
   if response["status"]==0:return error(response["message"])
   otp=response["message"]
   #logic
   response=await send_email_resend(resend_key,"https://api.resend.com/emails",sender_email,[email],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   if response["status"]==0:return error(response["message"])
   #final
   return response

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
   response=await openai_prompt(openai_client,model,prompt,is_web_search,previous_response_id)
   if response["status"]==0:return response
   #final
   return response

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
      "api_id":api_id,
      "redis":await redis_client.info() if redis_client else None,
      "postgres_schema":postgres_schema,
      "postgres_column_datatype":postgres_column_datatype,
      "users_api_access_count":len(users_api_access),
      "users_is_active_count":len(users_is_active),
      "bucket":s3_client.list_buckets() if s3_client else None,
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True)),
      "users_count":await postgres_client.fetch_all(query="select count(*) from users where is_active is distinct from 0;",values={}),
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
   response=await s3_file_upload_direct(s3_client,s3_region_name,bucket,key_list,file_list)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   #param
   object=await request.json()
   bucket=object.get("bucket")
   key=object.get("key")
   if not bucket or not key:return error("bucket/key missing")
   #logic
   response=await s3_file_upload_presigned(s3_client,s3_region_name,bucket,key,1000,100)
   if response["status"]==0:return error(response["message"])
   #final
   return response

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
   response=await postgres_query_runner(postgres_client,query,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   #final
   return response

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
            except Exception as e:print(e.args)
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
            except Exception as e:print(e.args)
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