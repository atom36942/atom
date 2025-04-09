async def get_users_is_active(postgres_client_asyncpg,limit):
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

async def get_users_api_access(postgres_client_asyncpg,limit):
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

from databases import Database
async def client_postgres(postgres_url):
   postgres_client=Database(postgres_url,min_size=1,max_size=100)
   await postgres_client.connect()
   return postgres_client

import asyncpg
async def client_postgres_asyncpg(postgres_url):
   postgres_client_asyncpg=await asyncpg.connect(postgres_url)
   return postgres_client_asyncpg

async def postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list[0]:return {"status":0,"message":"object missing"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   column_insert_list=list(object_list[0].keys())
   query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():
         output=await postgres_client.execute_many(query=query,values=object_list)
   return {"status":1,"message":output}

async def postgres_update(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list[0]:return {"status":0,"message":"object missing"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():
         output=await postgres_client.execute_many(query=query,values=object_list)
   return {"status":1,"message":output}

async def postgres_update_self(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize,user_id):
   if not object_list[0]:return {"status":0,"message":"object missing"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id and created_by_id={user_id} returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():
         output=await postgres_client.execute_many(query=query,values=object_list)
   return {"status":1,"message":output}

async def postgres_delete(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list[0]:return {"status":0,"message":"object missing"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   query=f"delete from {table} where id=:id;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():
         output=await postgres_client.execute_many(query=query,values=object_list)
   return {"status":1,"message":output}

async def postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string):
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   column=object.get("column","*")
   location_filter=object.get("location_filter")
   if location_filter:
      location_filter_split=location_filter.split(",")
      long,lat,min_meter,max_meter=float(location_filter_split[0]),float(location_filter_split[1]),int(location_filter_split[2]),int(location_filter_split[3])
   response=await create_where_string(object,object_serialize,postgres_column_datatype)
   if response["status"]==0:return response
   where_string,where_value=response["message"][0],response["message"][1]
   if location_filter:query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
   else:query=f"select {column} from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   return {"status":1,"message":object_list}

import hashlib,datetime,json
async def object_serialize(postgres_column_datatype,object_list):
   for index,object in enumerate(object_list):
      for key,value in object.items():
         datatype=postgres_column_datatype.get(key)
         if not datatype:return {"status":0,"message":f"column {key} is not in postgres schema"}
         elif value==None:continue
         elif key in ["password"]:object_list[index][key]=hashlib.sha256(str(value).encode()).hexdigest()
         elif datatype=="text" and value in ["","null"]:object_list[index][key]=None
         elif datatype=="text":object_list[index][key]=value.strip()
         elif "int" in datatype:object_list[index][key]=int(value)
         elif datatype=="numeric":object_list[index][key]=round(float(value),3)
         elif datatype=="date":object_list[index][key]=datetime.datetime.strptime(value,'%Y-%m-%d')
         elif "time" in datatype:object_list[index][key]=datetime.datetime.strptime(value,'%Y-%m-%dT%H:%M:%S')
         elif datatype=="ARRAY":object_list[index][key]=value.split(",")
         elif datatype=="jsonb":object_list[index][key]=json.dumps(value)
   return {"status":1,"message":object_list}

async def create_where_string(object,object_serialize,postgres_column_datatype):
   object={k:v for k,v in object.items() if (k in postgres_column_datatype and k not in ["metadata","location","table","order","limit","page"] and v is not None)}
   where_operator={k:v.split(',',1)[0] for k,v in object.items()}
   where_value={k:v.split(',',1)[1] for k,v in object.items()}
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return response
   where_value=response["message"][0]
   where_string_list=[f"({key} {where_operator[key]} :{key} or :{key} is null)" for key in [*object]]
   where_string_joined=' and '.join(where_string_list)
   where_string=f"where {where_string_joined}" if where_string_joined else ""
   return {"status":1,"message":[where_string,where_value]}
   
async def verify_otp(postgres_client,otp,email,mobile):
   if not otp:return {"status":0,"message":"otp must"}
   if email:
      query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
      output=await postgres_client.fetch_all(query=query,values={"email":email})
   if mobile:
      query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
      output=await postgres_client.fetch_all(query=query,values={"mobile":mobile})
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
   return {"status":1,"message":"done"}

from google.oauth2 import id_token
from google.auth.transport import requests
def verify_google_token(google_client_id,google_token):
   try:
      request=requests.Request()
      id_info=id_token.verify_oauth2_token(google_token,request,google_client_id)
      output={"sub": id_info.get("sub"),"email": id_info.get("email"),"name": id_info.get("name"),"picture": id_info.get("picture"),"email_verified": id_info.get("email_verified")}
      response={"status":1,"message":output}
   except Exception as e:response={"status":0,"message":str(e)}
   return response

async def ownership_check(postgres_client,table,id,user_id):
   if table=="users":
      if id!=user_id:return {"status":0,"message":"object ownership issue"}
   if table!="users":
      output=await postgres_client.fetch_all(query=f"select created_by_id from {table} where id=:id;",values={"id":id})
      if not output:return {"status":0,"message":"no object"}
      if output[0]["created_by_id"]!=user_id:return {"status":0,"message":"object ownership issue"}
   return {"status":1,"message":"done"}

async def add_creator_data(postgres_client, object_list, user_key):
    if not object_list:return {"status": 1, "message": object_list}
    object_list = [dict(object) for object in object_list]
    created_by_ids = {str(object["created_by_id"]) for object in object_list if object.get("created_by_id")}
    users = {}
    if created_by_ids:
        query = f"SELECT * FROM users WHERE id IN ({','.join(created_by_ids)});"
        users = {str(user["id"]): dict(user) for user in await postgres_client.fetch_all(query=query, values={})}
    for object in object_list:
        created_by_id = str(object.get("created_by_id"))
        if created_by_id in users:
            for key in user_key.split(","):
                object[f"creator_{key}"] = users[created_by_id].get(key)
        else:
            for key in user_key.split(","):
                object[f"creator_{key}"] = None
    return {"status": 1, "message": object_list}

import uuid
from io import BytesIO
async def s3_file_upload(s3_client,s3_region_name,bucket,key_list,file_list):
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
   form_data_key={key:value for key,value in form_data.items() if isinstance(value,str)}
   form_data_file=[file for key,value in form_data.items() for file in form_data.getlist(key)  if key not in form_data_key and file.filename]
   return form_data_key,form_data_file

import json
async def redis_set_object(redis_client,key,expiry,object):
   object=json.dumps(object)
   if not expiry:output=await redis_client.set(key,object)
   else:output=await redis_client.setex(key,expiry,object)
   return {"status":1,"message":output}

import json
async def redis_get_object(redis_client,key):
   output=await redis_client.get(key)
   if output:output=json.loads(output)
   return {"status":1,"message":output}

import jwt,json,time
async def token_create(key_jwt,user):
   token_expire_sec=365*24*60*60
   user={"id":user["id"],"type":user["type"]}
   user=json.dumps(user,default=str)
   token=jwt.encode({"exp":time.time()+token_expire_sec,"data":user},key_jwt)
   return token

async def request_user_read(request,postgres_client):
   query="select * from users where id=:id;"
   values={"id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=dict(output[0]) if output else None
   response={"status":1,"message":user}
   if not user:response={"status":0,"message":"user not found"}
   return response

async def admin_check(request,api,api_id,users_api_access,postgres_client):
   if "admin/" not in api:return {"status":1,"message":"done"}
   api_id_value=api_id.get(api)
   if not api_id_value:return {"status":0,"message":"api id not mapped in backend"}
   user_api_access=users_api_access.get(request.state.user["id"],"absent")
   if user_api_access=="absent":
      output=await postgres_client.fetch_all(query="select id,api_access from users where id=:id;",values={"id":request.state.user["id"]})
      user=output[0] if output else None
      if not user:return {"status":0,"message":"user not found"}
      api_access_str=user["api_access"]
      if not api_access_str:return {"status":0,"message":"api access denied"}
      user_api_access=[int(item.strip()) for item in api_access_str.split(",")]
   if api_id_value not in user_api_access:return {"status":0,"message":"api access denied"}
   return {"status":1,"message":"done"}

async def is_active_check(request,api,users_is_active,postgres_client):
   for item in ["admin/","private","my/object-create"]:
      if item in api:
         user_is_active=users_is_active.get(request.state.user["id"],"absent")
         if user_is_active=="absent":
            output=await postgres_client.fetch_all(query="select id,is_active from users where id=:id;",values={"id":request.state.user["id"]})
            user=output[0] if output else None
            if not user:return {"status":0,"message":"user not found"}
            user_is_active=user["is_active"]
         if user_is_active==0:return {"status":0,"message":"user not active"}
   return {"status":1,"message":"done"}

from fastapi import responses
def error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})
