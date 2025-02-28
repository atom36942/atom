#function
async def postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list[0]:return {"status":0,"message":"object missing"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   column_insert_list=list(object_list[0].keys())
   query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   if len(object_list)==1:output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return {"status":1,"message":output}

async def postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count,table_id):
   column=object.get("column","*")
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   creator_data,action_count,location_filter=object.get("creator_data",None),object.get("action_count",None),object.get("location_filter",None)
   response=await create_where_string(postgres_column_datatype,object_serialize,object)
   if response["status"]==0:return response
   where_string,where_value=response["message"][0],response["message"][1]
   query=f"select {column} from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   if location_filter:
      long,lat,min_meter,max_meter=float(location_filter.split(",")[0]),float(location_filter.split(",")[1]),int(location_filter.split(",")[2]),int(location_filter.split(",")[3])
      query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   if creator_data:
      response=await add_creator_data(postgres_client,object_list,creator_data)
      if response["status"]==0:return response
      object_list=response["message"]
   if action_count:
      for action_table in action_count.split(","):
         response=await add_action_count(postgres_client,action_table,object_list,table_id.get(table))
         if response["status"]==0:return response
         object_list=response["message"]
   return {"status":1,"message":object_list}

async def postgres_update(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list[0]:return {"status":0,"message":"object missing"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=coalesce(:{item},{item})' for item in column_update_list])} where id=:id returning *;"
   if len(object_list)==1:output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return {"status":1,"message":output}

async def postgres_delete(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list[0]:return {"status":0,"message":"object missing"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   query=f"delete from {table} where id=:id;"
   if len(object_list)==1:output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return {"status":1,"message":output}

async def object_check(table_id,column_lowercase,object_list):
   for index,object in enumerate(object_list):
      for key,value in object.items():
         if key=="parent_table" and value is not None and int(value) not in list(table_id.values()):return {"status":0,"message":"parent_table id mismatch"}
         # elif key=="rating" and value is not None and not 0<=float(value)<=10:return {"status":0,"message":"rating should be between 1-10"}
         elif key in column_lowercase:object_list[index][key]=value.strip().lower()
   return {"status":1,"message":object_list}

import hashlib,datetime,json
async def object_serialize(postgres_column_datatype,object_list):
   for index,object in enumerate(object_list):
      for key,value in object.items():
         datatype=postgres_column_datatype.get(key)
         if not datatype:return {"status":0,"message":f"column {key} is not in postgres schema"}
         elif value==None:continue
         elif key in ["password","google_id","apple_id","facebook_id","github_id","twitter_id"]:object_list[index][key]=hashlib.sha256(str(value).encode()).hexdigest()
         elif datatype=="text" and value=="":object_list[index][key]=None
         elif datatype=="text":object_list[index][key]=value.strip()
         elif "int" in datatype:object_list[index][key]=int(value)
         elif datatype=="numeric":object_list[index][key]=round(float(value),3)
         elif "time" in datatype or datatype=="date":object_list[index][key]=datetime.datetime.strptime(value,'%Y-%m-%dT%H:%M:%S')
         elif datatype=="ARRAY":object_list[index][key]=value.split(",")
         elif datatype=="jsonb":object_list[index][key]=json.dumps(value)
   return {"status":1,"message":object_list}

async def create_where_string(postgres_column_datatype,object_serialize,object):
   object={k:v for k,v in object.items() if k in postgres_column_datatype}
   object={k:v for k,v in object.items() if v is not None}
   object={k:v for k,v in object.items() if k not in ["metadata","location","table","order","limit","page"]}
   where_operator={k:v.split(',',1)[0] for k,v in object.items()}
   where_value={k:v.split(',',1)[1] for k,v in object.items()}
   column_read_list=[*object]
   where_column_single_list=[f"({column} {where_operator[column]} :{column} or :{column} is null)" for column in column_read_list]
   where_column_joined=' and '.join(where_column_single_list)
   where_string=f"where {where_column_joined}" if where_column_joined else ""
   response=await object_serialize(postgres_column_datatype,[where_value])
   if response["status"]==0:return response
   where_value=response["message"][0]
   return {"status":1,"message":[where_string,where_value]}

async def add_creator_data(postgres_client,object_list,user_key):
   if not object_list:return {"status":1,"message":object_list}
   object_list=[dict(object) for object in object_list]
   created_by_ids={str(object["created_by_id"]) for object in object_list if object.get("created_by_id")}
   if created_by_ids:
      query=f"SELECT * FROM users WHERE id IN ({','.join(created_by_ids)});"
      users={user["id"]:dict(user) for user in await postgres_client.fetch_all(query=query, values={})}
   for object in object_list:
      if object["created_by_id"] in users:
         for key in user_key.split(","):object[f"creator_{key}"]=users[object["created_by_id"]][key]
      else:
         for key in user_key.split(","):object[f"creator_{key}"]=None    
   return {"status":1,"message":object_list}

async def add_action_count(postgres_client,action_table,object_list,object_table_id):
   if not object_list:return {"status":1,"message":object_list}
   key_name=f"{action_table}_count"
   object_list=[dict(item)|{key_name:0} for item in object_list]
   parent_ids_list=[str(item["id"]) for item in object_list if item["id"]]
   parent_ids_string=",".join(parent_ids_list)
   if parent_ids_string:
      query=f"select parent_id,count(*) from {action_table} where parent_table=:parent_table and parent_id in ({parent_ids_string}) group by parent_id;"
      query_param={"parent_table":object_table_id}
      object_list_action=await postgres_client.fetch_all(query=query,values=query_param)
      for x in object_list:
         for y in object_list_action:
               if x["id"]==y["parent_id"]:
                  x[key_name]=y["count"]
                  break
   return {"status":1,"message":object_list}

async def ownership_check(postgres_client,table,id,user_id):
   if table=="users":
      if id!=user_id:return {"status":0,"message":"object ownership issue"}
   if table!="users":
      output=await postgres_client.fetch_all(query=f"select created_by_id from {table} where id=:id;",values={"id":id})
      if not output:return {"status":0,"message":"no object"}
      if output[0]["created_by_id"]!=user_id:return {"status":0,"message":"object ownership issue"}
   return {"status":1,"message":"done"}

async def verify_otp(postgres_client,otp,email,mobile):
   if not otp:return {"status":0,"message":"otp must"}
   if email:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;",values={"email":email})
   if mobile:output=await postgres_client.fetch_all(query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;",values={"mobile":mobile})
   if not output:return {"status":0,"message":"otp not found"}
   if int(output[0]["otp"])!=int(otp):return {"status":0,"message":"otp mismatch"}
   return {"status":1,"message":"done"}

import json,jwt
async def auth_check(request,key_root,key_jwt):
   user={}
   api=request.url.path
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   token_decode=lambda t:json.loads(jwt.decode(t,key_jwt,algorithms="HS256")["data"])
   if "root/" in api and token!=key_root:return {"status":0,"message":"root token mismatch"}
   elif "my/" in api:user=token_decode(token)
   elif "private/" in api:user=token_decode(token)
   elif "admin/" in api:user=token_decode(token)
   return {"status":1,"message":user}

async def admin_check(user,request,api_id,users_api_access,postgres_client):
   if "admin/" not in api:return {"status":1,"message":"not needed"}
   api=request.url.path
   if not api_id.get(api):return {"status":0,"message":"api_id not mapped in backend"}
   api_id_value=api_id.get(api)
   user_api_access=users_api_access.get(user["id"],"absent")
   if user_api_access=="absent":
      output=await postgres_client.fetch_all(query="select id,api_access from users where id=:id;",values={"id":user["id"]})
      if not output:return {"status":0,"message":"user not found"}
      api_access_str=output[0]["api_access"]
      if not api_access_str:return {"status":0,"message":"api access denied"}
      user_api_access=[int(item.strip()) for item in api_access_str.split(",")]
   if api_id_value not in user_api_access:return {"status":0,"message":"api access denied"}
   return {"status":1,"message":"done"}

async def is_active_check(user,request,api_is_active_check,users_is_active,postgres_client):
   api=request.url.path
   for item in api_is_active_check:
      if item in api:
         user_is_active=users_is_active.get(user["id"],"absent")
         if user_is_active=="absent":
            output=await postgres_client.fetch_all(query="select id,is_active from users where id=:id;",values={"id":user["id"]})
            if not output:return {"status":0,"message":"user not found"}
            user_is_active=output[0]["is_active"]
         if user_is_active==0:return {"status":0,"message":"you are not active"}
   return {"status":1,"message":"done"}

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

async def postgres_schema_init(postgres_client,postgres_schema_read,config):
   #extension
   await postgres_client.fetch_all(query="create extension if not exists postgis;",values={})
   await postgres_client.fetch_all(query="create extension if not exists pg_trgm;",values={})
   #table
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column_list in config["table"].items():
      is_table=postgres_schema.get(table,{})
      if not is_table:await postgres_client.execute(query=f"create table if not exists {table} (id bigint primary key generated always as identity not null);",values={})
   #column
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column_list in config["table"].items():
      for column in column_list:
         column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
         is_column=postgres_schema.get(table,{}).get(column_name,{})
         if not is_column:await postgres_client.execute(query=f"alter table {table} add column if not exists {column_name} {column_datatype};",values={})
   #nullable
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column_list in config["table"].items():
      for column in column_list:
         column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
         is_null=postgres_schema.get(table,{}).get(column_name,{}).get("is_null",None)
         if column_is_mandatory=="0" and is_null==0:await postgres_client.execute(query=f"alter table {table} alter column {column_name} drop not null;",values={})
         if column_is_mandatory=="1" and is_null==1:await postgres_client.execute(query=f"alter table {table} alter column {column_name} set not null;",values={})
   #index
   postgres_schema=await postgres_schema_read(postgres_client)
   index_name_list=[object["indexname"] for object in (await postgres_client.fetch_all(query="SELECT indexname FROM pg_indexes WHERE schemaname='public';",values={}))]
   for table,column_list in config["table"].items():
      for column in column_list:
         column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
         if column_index_type=="0":await postgres_client.execute(query=f"DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname ILIKE 'index_{table}_{column_name}_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;",values={})
         else:
            index_type_list=column_index_type.split(",")
            for index_type in index_type_list:
               index_name=f"index_{table}_{column_name}_{index_type}"
               if index_name not in index_name_list:
                  if index_type=="gin":await postgres_client.execute(query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name} gin_trgm_ops);",values={})
                  else:await postgres_client.execute(query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name});",values={})
   #query
   constraint_name_list={object["constraint_name"].lower() for object in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))}
   for query in config["query"].values():
      if query.split()[0]=="0":continue
      if "add constraint" in query.lower() and query.split()[5].lower() in constraint_name_list:continue
      await postgres_client.fetch_all(query=query,values={})
   #final
   return {"status":1,"message":"done"}

async def postgres_schema_read(postgres_client):
   postgres_schema={}
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
   for object in output:
      table,column=object["table"],object["column"]
      column_data={"datatype":object["datatype"],"default":object["default"],"is_null":object["is_null"],"is_index":object["is_index"]}
      if table not in postgres_schema:postgres_schema[table]={}
      postgres_schema[table][column]=column_data
   return postgres_schema

import csv,io
async def file_to_object_list(file):
   content=await file.read()
   csv_text=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(csv_text))
   object_list=[row for row in reader]
   await file.close()
   return object_list

async def read_body_form(request):
   body_form=await request.form()
   body_form_key={key:value for key,value in body_form.items() if isinstance(value,str)}
   body_form_file=[file for key,value in body_form.items() for file in body_form.getlist(key)  if key not in body_form_key and file.filename]
   return body_form_key,body_form_file

from fastapi import responses
def error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})

#env
import os,json
from dotenv import load_dotenv
load_dotenv()
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
s3_region_name=os.getenv("s3_region_name")
sns_region_name=os.getenv("sns_region_name")
ses_region_name=os.getenv("ses_region_name")
mongodb_cluster_url=os.getenv("mongodb_cluster_url")
channel_name=os.getenv("channel_name","ch1")
log_api_reset_count=int(os.getenv("log_api_reset_count",10))
token_expire_sec=int(os.getenv("token_expire_sec",365*24*60*60))
max_ids_length_delete=int(os.getenv("max_ids_length_delete",3))
table_id=json.loads(os.getenv("table_id",'{"users":1,"post":2,"atom":3,"action_comment":4,"human":5}'))
account_delete_mode=os.getenv("account_delete_mode","soft")
is_index_html=int(os.getenv("is_index_html",0))
is_signup=int(os.getenv("is_signup",0))

#globals
object_list_log_api=[]
output_cache_info={}
column_disabled_non_admin=["is_active","is_verified","api_access"]
column_lowercase=["type","tag","status","email","mobile","country","state","city","work_profile","skill"]
api_id={
"/admin/db-runner":1,
"/admin/object-update":2,
"/admin/object-read":3,
"/admin/ids-delete":4,
"/admin/ids-update":5,
}
query_human_work_profile="select distinct(trim(work_profile)) as work_profile from human where is_active=1 and type in ('jobseeker','intern','freelancer','consultant') limit 100000;"
query_human_skill='''
with 
x as (select distinct(trim(unnest(string_to_array(skill, ',')))) as skill from human where is_active=1 and type in ('jobseeker','intern','freelancer','consultant') and skill is not null)
select skill from x limit 100000;
'''
postgres_config={
"table":{
"human":[
"created_at-timestamptz-0-brin",
"created_by_id-bigint-0-btree",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_protected-smallint-0-btree",
"is_deleted-smallint-0-btree",
"remark-text-0-gin,btree",
"rating-numeric(10,3)-0-btree",
"type-text-0-gin,btree",
"name-text-0-0",
"gender-text-0-0",
"email-text-0-0",
"mobile-text-0-0",
"country-text-0-0",
"state-text-0-0",
"city-text-0-gin",
"experience-numeric(10,1)-0-btree",
"work_profile-text-0-gin",
"skill-text-0-gin",
"description-text-0-0",
"linkedin_url-text-0-0",
"portfolio_url-text-0-0",
"website_url-text-0-0",
"resume_url-text-0-0"
],
"test":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-0",
"type-text-0-0",
"title-text-0-0",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0"
],
"atom":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-btree",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"type-text-1-gin",
"title-text-0-0",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0",
"parent_table-smallint-0-btree",
"parent_id-bigint-0-btree",
"rating-numeric(10,3)-0-0"
],
"project":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_protected-smallint-0-btree",
"is_deleted-smallint-0-btree",
"type-text-1-gin",
"title-text-0-0",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0"
],
"users":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_protected-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"type-text-0-gin",
"username-text-0-btree",
"password-text-0-btree",
"location-geography(POINT)-0-gist",
"metadata-jsonb-0-0",
"google_id-text-0-btree",
"last_active_at-timestamptz-0-0",
"date_of_birth-date-0-0",
"email-text-0-btree",
"mobile-text-0-btree",
"name-text-0-0",
"city-text-0-gin",
"api_access-text-0-0",
"rating-numeric(10,3)-0-0"
],
"post":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-btree",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-text-0-gin",
"title-text-0-0",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-gin",
"location-geography(POINT)-0-0",
"metadata-jsonb-0-0",
"rating-numeric(10,3)-0-0"
],
"message":[
"created_at-timestamptz-0-brin",
"created_by_id-bigint-1-btree",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"user_id-bigint-1-btree",
"description-text-1-0",
"is_read-smallint-0-btree"
],
"helpdesk":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-btree",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"status-text-0-gin",
"remark-text-0-0",
"type-text-0-gin",
"description-text-1-0",
"email-text-0-0"
],
"otp":[
"created_at-timestamptz-1-brin",
"otp-integer-1-0",
"email-text-0-btree",
"mobile-text-0-btree"
],
"log_api":[
"created_at-timestamptz-1-brin",
"created_by_id-bigint-0-0",
"method-text-0-0",
"api-text-0-0",
"query_param-text-0-0",
"status_code-smallint-0-0",
"response_time_ms-numeric(1000,3)-0-0",
"is_deleted-smallint-0-btree",
"description-text-0-0"
],
"log_password":[
"created_at-timestamptz-1-0",
"user_id-bigint-0-0",
"password-text-0-0",
"is_deleted-smallint-0-0"
],
"action_like":[
"created_at-timestamptz-1-0",
"created_by_id-bigint-1-btree",
"is_deleted-smallint-0-btree",
"parent_table-smallint-1-btree",
"parent_id-bigint-1-btree"
],
"action_bookmark":[
"created_at-timestamptz-1-0",
"created_by_id-bigint-1-btree",
"is_deleted-smallint-0-btree",
"parent_table-smallint-1-btree",
"parent_id-bigint-1-btree"
],
"action_report":[
"created_at-timestamptz-1-0",
"created_by_id-bigint-1-btree",
"is_deleted-smallint-0-btree",
"parent_table-smallint-1-btree",
"parent_id-bigint-1-btree"
],
"action_block":[
"created_at-timestamptz-1-0",
"created_by_id-bigint-1-btree",
"is_deleted-smallint-0-btree",
"parent_table-smallint-1-btree",
"parent_id-bigint-1-btree"
],
"action_follow":[
"created_at-timestamptz-1-0",
"created_by_id-bigint-1-btree",
"is_deleted-smallint-0-btree",
"parent_table-smallint-1-btree",
"parent_id-bigint-1-btree"
],
"action_rating":[
"created_at-timestamptz-1-0",
"created_by_id-bigint-1-btree",
"is_deleted-smallint-0-btree",
"parent_table-smallint-1-btree",
"parent_id-bigint-1-btree",
"rating-numeric(10,3)-1-0"
],
"action_comment":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"updated_at-timestamptz-0-0",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"parent_table-smallint-1-btree",
"parent_id-bigint-1-btree",
"description-text-1-0"
]
},
"query":{
"delete_disable_bulk_function":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;",
"delete_disable_bulk_users":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"delete_disable_bulk_human":"create or replace trigger trigger_delete_disable_bulk_human after delete on human referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"default_created_at":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='created_at' AND table_schema='public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"default_updated_at_1":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';",
"default_updated_at_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"default_is_protected_users":"ALTER TABLE users ALTER COLUMN is_protected SET DEFAULT 1;",
"default_is_protected_project":"ALTER TABLE project ALTER COLUMN is_protected SET DEFAULT 1;",
"default_is_protected_human":"ALTER TABLE human ALTER COLUMN is_protected SET DEFAULT 1;",
"rule_is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected=1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"root_user_1":"insert into users (username,password,api_access) values ('atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3','1,2,3,4,5,6,7,8,9,10') on conflict do nothing;",
"root_user_2":"create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"log_password_1":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;",
"log_password_2":"CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"unique_users_username":"alter table users add constraint constraint_unique_users_username unique (username);",
"unique_acton_like":"alter table action_like add constraint constraint_unique_action_like_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_bookmark":"alter table action_bookmark add constraint constraint_unique_action_bookmark_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_report":"alter table action_report add constraint constraint_unique_action_report_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_block":"alter table action_block add constraint constraint_unique_action_block_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_follow":"alter table action_follow add constraint constraint_unique_action_follow_cpp unique (created_by_id,parent_table,parent_id);",
"check_is_active":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_active' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_active', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_active IN (0,1) OR is_active IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_is_protected":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_protected' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_protected', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_protected IN (0,1) OR is_protected IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_is_deleted":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_deleted' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_deleted', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_deleted IN (0,1) OR is_deleted IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_is_verified":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_verified' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_verified', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_verified IN (0,1) OR is_verified IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_is_read":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_read' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_read', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_read IN (0,1) OR is_read IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_rating_1":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'rating' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_rating', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (rating BETWEEN 0 AND 10);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_rating_2":"0 DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tablename IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'rating')) LOOP EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS constraint_check_%I_rating;', r.tablename, r.tablename); END LOOP; END $$;",
"check_users_username":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"drop_all_index":"0 DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'index_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;"
}
}

#setters
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
   postgres_schema=await postgres_schema_read(postgres_client)
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return None

users_api_access={}
async def set_users_api_access():
   global users_api_access
   users_api_access={}
   order,limit="id desc",10000
   if postgres_schema.get("users"):
      for page in range(1,101):
         output=await postgres_client.fetch_all(query=f"select id,api_access from users where api_access is not null  order by {order} limit {limit} offset {(page-1)*limit};",values={})
         if not output:break
         users_api_access={object["id"]:[int(item.strip()) for item in object["api_access"].split(",")] for object in output if len(object["api_access"])>=1}
   return None

users_is_active={}
async def set_users_is_active():
   global users_is_active
   users_is_active={}
   order,limit="id desc",10000
   if postgres_schema.get("users"):
      for page in range(1,101):
         output=await postgres_client.fetch_all(query=f"select id,is_active from users order by {order} limit {limit} offset {(page-1)*limit};",values={})
         if not output:break
         users_is_active={object["id"]:object["is_active"] for object in output}
   return None

project_data={}
async def set_project_data():
   global project_data
   project_data={}
   order,limit="id desc",1000
   if postgres_schema.get("project"):
      for page in range(1,11):
         output=await postgres_client.fetch_all(query=f"select * from project order by {order} limit {limit} offset {(page-1)*limit};;",values={})
         if not output:break
         for object in output:
            if object["type"] not in project_data:project_data[object["type"]]=[object]
            else:project_data[object["type"]]+=[object]
   return None

redis_client=None
redis_pubsub=None
import redis.asyncio as redis
async def set_redis_client():
   global redis_client
   global redis_pubsub
   if redis_server_url:
      redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(os.getenv("redis_server_url")))
      redis_pubsub=redis_client.pubsub()
      await redis_pubsub.subscribe(channel_name)
   return None

mongodb_client=None
import motor.motor_asyncio
async def set_mongodb_client():
   global mongodb_client
   if mongodb_cluster_url:mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(mongodb_cluster_url)
   return None

s3_client=None
s3_resource=None
import boto3
async def set_s3_client():
   global s3_client,s3_resource
   if s3_region_name:
      s3_client=boto3.client("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
      s3_resource=boto3.resource("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

sns_client=None
import boto3
async def set_sns_client():
   global sns_client
   if sns_region_name:
      sns_client=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

ses_client=None
import boto3
async def set_ses_client():
   global ses_client
   if ses_region_name:
      ses_client=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

rabbitmq_client=None
rabbitmq_channel=None
import pika
async def set_rabbitmq_client():
   global rabbitmq_client
   global rabbitmq_channel
   if rabbitmq_server_url:
      rabbitmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("rabbitmq_server_url")))
      rabbitmq_channel=rabbitmq_client.channel()
      rabbitmq_channel.queue_declare(queue=channel_name)
   return None

lavinmq_client=None
lavinmq_channel=None
import pika
async def set_lavinmq_client():
   global lavinmq_client
   global lavinmq_channel
   if lavinmq_server_url:
      lavinmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("lavinmq_server_url")))
      lavinmq_channel=lavinmq_client.channel()
      lavinmq_channel.queue_declare(queue=channel_name)
   return None

kafka_producer_client=None
kafka_consumer_client=None
from aiokafka import AIOKafkaProducer
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def set_kafka_client():
   global kafka_producer_client
   global kafka_consumer_client
   if kafka_server_url:
      context=create_ssl_context(cafile=os.getenv("kafka_path_cafile"),certfile=os.getenv("kafka_path_certfile"),keyfile=os.getenv("kafka_path_keyfile"))
      kafka_producer_client=AIOKafkaProducer(bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context)
      kafka_consumer_client=AIOKafkaConsumer(channel_name,bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
      await kafka_producer_client.start()
      await kafka_consumer_client.start()
   return None

#sentry
import sentry_sdk
if sentry_dsn:
   sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

#redis key builder
from fastapi import Request,Response
import jwt,json
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param=str(dict(sorted(request.query_params.items())))
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   user_id=0
   if token and "my/" in api:user_id=json.loads(jwt.decode(token,os.getenv("key_jwt"),algorithms="HS256")["data"])["id"]
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_users_api_access()
   await set_users_is_active()
   await set_project_data()
   await set_redis_client()
   await set_s3_client()
   await set_sns_client()
   await set_ses_client()
   await set_mongodb_client()
   await set_rabbitmq_client()
   await set_lavinmq_client()
   await set_kafka_client()
   if redis_server_url:
      await FastAPILimiter.init(redis_client)
      FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   yield
   try:
      await postgres_client.disconnect()
      if redis_server_url:await redis_client.aclose()
      if rabbitmq_server_url and rabbitmq_channel.is_open:rabbitmq_channel.close()
      if rabbitmq_server_url and rabbitmq_client.is_open:rabbitmq_client.close()
      if lavinmq_server_url and lavinmq_channel.is_open:lavinmq_channel.close()
      if lavinmq_server_url and lavinmq_client.is_open:lavinmq_client.close()
      if kafka_server_url:await kafka_producer_client.stop()
   except Exception as e:print(e.args)

#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

from fastapi import responses
from starlette.background import BackgroundTask
async def add_api_background(request,api_function):
   response=None
   query_param=dict(request.query_params)
   if query_param.get("is_background",None)=="1":
      body=await request.body()
      async def receive():return {"type":"http.request","body":body}
      async def api_function_new():
         request_new=Request(scope=request.scope,receive=receive)
         await api_function(request_new)
      response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
      response.background=BackgroundTask(api_function_new)
   return response

#middleware
from fastapi import Request,responses
import time,traceback
from starlette.background import BackgroundTask
@app.middleware("http")
async def middleware(request:Request,api_function):
   start=time.time()
   global object_list_log_api
   method=request.method
   api=request.url.path
   query_param=dict(request.query_params)
   body=await request.body()
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   user={}
   error_text=None
   #try
   try:
      #auth
      if any(item in api for item in ["root/","my/", "private/", "admin/"]) and not token:return error("Bearer token must")
      if token:
         if "root/" in api:
            if token!=key_root:return error("key root mismatch")
         else:
            user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
            if not user.get("id",None):return error("user_id not in token")
            if "admin/" in api:
               if not api_id.get(api):return error("api_id not mapped in backend")
               api_id_value=api_id.get(api)
               user_api_access=users_api_access.get(user["id"],"absent")
               if user_api_access=="absent":
                  output=await postgres_client.fetch_all(query="select id,api_access from users where id=:id;",values={"id":user["id"]})
                  if not output:return error("user not found")
                  api_access_str=output[0]["api_access"]
                  if not api_access_str:return error("api access denied")
                  user_api_access=[int(item.strip()) for item in api_access_str.split(",")]
               if api_id_value not in user_api_access:return error("api access denied") 
            for item in ["admin/","my/object-create","private/human-read"]:
               if item in api:
                  user_is_active=users_is_active.get(user["id"],"absent")
                  if user_is_active=="absent":
                     output=await postgres_client.fetch_all(query="select id,is_active from users where id=:id;",values={"id":user["id"]})
                     if not output:return error("user not found")
                     user_is_active=output[0]["is_active"]
                  if user_is_active==0:return error ("user not active")
      request.state.user=user
      #api response
      if query_param.get("is_background")=="1":
         async def receive():return {"type":"http.request","body":body}
         async def api_function_new():
            request_new=Request(scope=request.scope,receive=receive)
            await api_function(request_new)
         response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
         response.background=BackgroundTask(api_function_new)
      else:response=await api_function(request) 
   #exception
   except Exception as e:
      print(traceback.format_exc())
      error_text=str(e.args)
      response=error(error_text)
   #final
   response_time_ms=(time.time()-start)*1000
   object={"created_by_id":user.get("id",None),"method":method,"api":api,"query_param":json.dumps(query_param),"status_code":response.status_code,"response_time_ms":response_time_ms,"description":error_text}
   object_list_log_api.append(object)
   if postgres_schema.get("log_api") and len(object_list_log_api)>=log_api_reset_count and not query_param.get("is_background"):
      response.background=BackgroundTask(postgres_create,"log_api",object_list_log_api,0,postgres_client,postgres_column_datatype,object_serialize)
      object_list_log_api=[]
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
      
#api import
from fastapi import Request,UploadFile,Depends,BackgroundTasks,responses
import hashlib,datetime,json,time,jwt,os,random
from typing import Literal
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter

#index
@app.get("/")
async def root():
   response={"status":1,"message":"welcome to atom"}
   if is_index_html==1:response=responses.FileResponse("index.html")
   return response

#db init
@app.post("/root/db-init")
async def root_db_init(request:Request):
   query_param=dict(request.query_params)
   mode=query_param.get("mode",None)
   if not mode:return error("mode missing")
   if mode=="default":config=postgres_config
   if mode=="custom":config=await request.json()
   response=await postgres_schema_init(postgres_client,postgres_schema_read,config)
   await set_postgres_schema()
   return response

#db runner
@app.post("/root/db-runner")
async def root_db_runner(request:Request):
   body_json=await request.json()
   query=body_json.get("query",None)
   if not query:return error("body json query missing")
   stop_word=["drop","truncate"]
   for item in stop_word:
       if item in query.lower():return error(f"{item} keyword not allowed in query")
   output=[]
   async with postgres_client.transaction():
      for query in query.split("---"):
         result=await postgres_client.fetch_all(query=query,values={})
         output.append(result)
   return {"status":1,"message":output}

@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   body_json=await request.json()
   query=body_json.get("query",None)
   if not query:return error("body json query missing")
   must_word=["select"]
   stop_word=["drop","delete","update","insert","alter","truncate","create", "rename","replace","merge","grant","revoke","execute","call","comment","set","disable","enable","lock","unlock"]
   for item in must_word:
      if item not in query.lower():return error(f"{item} keyword must be present in query")
   for item in stop_word:
       if item in query.lower():return error(f"{item} keyword not allowed in query")
   output=await postgres_client.fetch_all(query=query,values={})
   return {"status":1,"message":output}

#db uploader
@app.post("/root/db-uploader")
async def root_db_uploader(request:Request):
   body_form_key,body_form_file=await read_body_form(request)
   mode,table=body_form_key.get("mode",None),body_form_key.get("table",None)
   if not mode or not table:return error("body form mode/table missing")
   if not body_form_file:return error("body form file missing")
   object_list=await file_to_object_list(body_form_file[-1])
   response=await object_check(table_id,column_lowercase,object_list)
   if response["status"]==0:return error(response["message"])
   object_list=response["message"]
   if mode=="create":response=await postgres_create(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="update":response=await postgres_update(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="delete":response=await postgres_delete(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   return response

#ops
@app.delete("/root/db-clean")
async def root_db_clean():
   await postgres_client.execute(query="delete from log_api where created_at<now()-interval '100 days';",values={})
   await postgres_client.execute(query="delete from log_password where created_at<now()-interval '1000 days';",values={})
   await postgres_client.execute(query="delete from otp where created_at<now()-interval '100 days';",values={})
   await postgres_client.execute(query="delete from message where created_at<now()-interval '1000 days';",values={})
   [await postgres_client.execute(query=f"delete from {table} where created_by_id not in (select id from users);",values={}) for table in [*postgres_schema] if "action_" in table]
   [await postgres_client.execute(query=f"delete from {table} where parent_table={table_id.get(parent_table,0)} and parent_id not in (select id from {parent_table});",values={}) for table in [*postgres_schema] for parent_table in [*table_id] if "action_" in table]
   [await postgres_client.execute(query=f"delete from {table} where parent_table not in ({','.join([str(id) for id in table_id.values()])});",values={}) for table in [*postgres_schema] if "action_" in table]
   await postgres_client.execute(query="update human set is_protected=null where is_deleted=1;",values={})
   [await postgres_client.execute(query="delete from human where id=:id;",values={"id":object["id"]}) for object in await postgres_client.fetch_all(query="select id from human where is_deleted=1 limit 100;",values={})]
   return {"status":1,"message":"done"}

@app.put("/root/db-checklist")
async def root_db_checklist():
   await postgres_client.execute(query="update users set is_active=null,is_deleted=null where id=1;",values={})
   await postgres_client.execute(query="update users set is_protected=1 where api_access is not null;",values={})
   await postgres_client.execute(query="update users set is_active=0 where is_deleted=1;",values={})
   await postgres_client.execute(query="update human set is_active=0 where is_deleted=1;",values={})
   await postgres_client.execute(query="update human set remark=null where remark='';",values={})
   return {"status":1,"message":"done"}

@app.put("/root/reset-global")
async def root_reset_global():
   await set_postgres_schema()
   await set_project_data()
   await set_users_api_access()
   await set_users_is_active()
   return {"status":1,"message":"done"}

#redis
@app.post("/root/redis-set-object")
async def root_redis_set_object(request:Request):
   query_param=dict(request.query_params)
   key=query_param.get("key",None)
   expiry=query_param.get("expiry",None)
   if not key:return error("query param key missing")
   body_json=await request.json()
   if not expiry:output=await redis_client.set(key,json.dumps(body_json))
   else:output=await redis_client.setex(key,expiry,json.dumps(body_json))
   return {"status":1,"message":output}

@app.get("/public/redis-get-object")
async def public_redis_get_object(request:Request):
   query_param=dict(request.query_params)
   key=query_param.get("key",None)
   if not key:return error("query param key missing")
   output=await redis_client.get(key)
   if output:output=json.loads(output)
   return {"status":1,"message":output}

@app.post("/root/redis-set-csv")
async def root_redis_set_csv(request:Request):
   body_form_key,body_form_file=await read_body_form(request)
   table,expiry=body_form_key.get("table",None),body_form_key.get("expiry",None)
   if not table:return error("body form table missing")
   if not body_form_file:return error("body form file missing")
   object_list=await file_to_object_list(body_form_file[-1])
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if not expiry:pipe.set(key,json.dumps(object))
         else:pipe.setex(key,expiry,json.dumps(object))
      await pipe.execute()
   return {"status":1,"message":"done"}

@app.delete("/root/redis-reset")
async def root_reset_redis():
   await redis_client.flushall()
   return {"status":1,"message":"done"}

#s3
@app.get("/root/s3-bucket-list")
async def root_s3_bucket_list():
   output=s3_client.list_buckets()
   return {"status":1,"message":output}

@app.post("/root/s3-bucket-create")
async def root_s3_bucket_create(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   output=s3_client.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})
   return {"status":1,"message":output}

@app.put("/root/s3-bucket-public")
async def root_s3_bucket_public(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return {"status":1,"message":output}

@app.delete("/root/s3-bucket-empty")
async def root_s3_bucket_empty(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   output=s3_resource.Bucket(bucket).objects.all().delete()
   return {"status":1,"message":output}

@app.delete("/root/s3-bucket-delete")
async def root_s3_bucket_empty(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   output=s3_client.delete_bucket(Bucket=bucket)
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   body_json=await request.json()
   url=body_json.get("url",None)
   if not url:return error("body json url missing")
   for item in url.split("---"):
      bucket,key=item.split("//",1)[1].split(".",1)[0],item.rsplit("/",1)[1]
      output=s3_resource.Object(bucket,key).delete()
   return {"status":1,"message":output}

@app.post("/private/s3-file-upload")
async def private_s3_file_upload(request:Request):
   body_form_key,body_form_file=await read_body_form(request)
   bucket,key=body_form_key.get("bucket",None),body_form_key.get("key",None)
   if not bucket or not key:return error("body form bucket/key missing")
   key_list=None if key=="uuid" else key.split("---")
   response=await s3_file_upload(s3_client,s3_region_name,bucket,key_list,body_form_file)
   if response["status"]==0:return error(response["message"])
   return response

@app.post("/private/s3-file-upload-presigned")
async def private_s3_file_upload_presigned(request:Request):
   body_json=await request.json()
   bucket,key=body_json.get("bucket",None),body_json.get("key",None)
   if not bucket or not key:return error("body json bucket/key missing")
   if "." not in key:return error("extension must")
   expiry_sec,size_kb=1000,100
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec,Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   return {"status":1,"message":output}

#auth
@app.post("/auth/signup",dependencies=[Depends(RateLimiter(times=1,seconds=3))])
async def auth_signup(request:Request):
   if is_signup==0:return error("signup disabled")
   body_json=await request.json()
   username,password=body_json.get("username"),body_json.get("password")
   if not username or not password:return error("body json username/password missing")
   query="insert into users (username,password) values (:username,:password) returning *;"
   query_param={"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.post("/auth/login-password")
async def auth_login(request:Request):
   body_json=await request.json()
   if len(body_json)!=2:return error("body length should be 2")
   password=body_json.get("password")
   if not password:return error("password missing")
   del body_json["password"]
   key,value=next(iter(body_json.items()))
   if key not in ["username","email","mobile"]:return error(f"{key} column not allowed")
   value=value.strip().lower()
   output=await postgres_client.fetch_all(query=f"select id from users where {key}=:key_value and password=:password order by id desc limit 1;",values={"key_value":value,"password":hashlib.sha256(str(password).encode()).hexdigest()})
   user=output[0] if output else None
   if not user:return error("user not found")
   token=jwt.encode({"exp":time.time()+token_expire_sec,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/auth/login-oauth")
async def auth_login_oauth(request:Request):
   body_json=await request.json()
   if len(body_json)!=1:return error("body length should be 1")
   key,value=next(iter(body_json.items()))
   if key not in ["google_id","apple_id","facebook_id","github_id","twitter_id"]:return error("oauth column not allowed")
   output=await postgres_client.fetch_all(query=f"select id from users where {key}=:key_value order by id desc limit 1;",values={"key_value":hashlib.sha256(value.encode()).hexdigest()})
   user=output[0] if output else None
   if not user:
      if is_signup==0:return error("signup disabled")
      if is_signup==1:
         output=await postgres_client.fetch_all(query=f"insert into users ({key}) values (:key_value) returning *;",values={"key_value":hashlib.sha256(value.encode()).hexdigest()})
         user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+token_expire_sec,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/auth/login-otp")
async def auth_login_otp(request:Request):
   body_json=await request.json()
   if len(body_json)!=2:return error("body length should be 2")
   otp=body_json.get("otp")
   if not otp:return error("otp missing")
   del body_json["otp"]
   key,value=next(iter(body_json.items()))
   if key not in ["email","mobile"]:return error(f"{key} column not allowed")
   if not value:return error("contact missing")
   value=value.strip().lower()
   if key=="email":response=await verify_otp(postgres_client,otp,value,None)
   else:response=await verify_otp(postgres_client,otp,None,value)
   if response["status"]==0:return error(response["message"])
   output=await postgres_client.fetch_all(query=f"select id from users where {key}=:key_value order by id desc limit 1;",values={"key_value":value})
   user=output[0] if output else None
   if not user:
      if is_signup==0:return error("signup disabled")
      if is_signup==1:
         output=await postgres_client.fetch_all(query=f"insert into users ({key}) values (:key_value) returning *;",values={"key_value":value})
         user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+token_expire_sec,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

#my
@app.get("/my/profile")
async def my_profile(request:Request,background:BackgroundTasks):
   column="*"
   query_param=dict(request.query_params)
   if query_param.get("column"):column=query_param.get("column")
   user=await postgres_client.fetch_all(query=f"select {column} from users where id=:id;",values={"id":request.state.user["id"]})
   if not user:return error("user not found")
   user=dict(user[0])
   if user["is_active"]!=0:user["is_active"]=1
   background.add_task(postgres_client.execute,query="update users set last_active_at=:last_active_at where id=:id",values={"id":request.state.user["id"],"last_active_at":datetime.datetime.now()})
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   token=jwt.encode({"exp":time.time()+token_expire_sec,"data":json.dumps({"id":request.state.user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def my_account_delete(request:Request):
   postgres_schema=await postgres_schema_read(postgres_client)
   output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   user=output[0] if output else None
   if not user:return error("user not found")
   if user["api_access"]:return {"status":1,"message":"access denied as you are admin"}
   if account_delete_mode=="soft":
      async with postgres_client.transaction():
         for table,column in postgres_schema.items():
            if table not in ["users"]:
               if column.get("created_by_id",None):await postgres_client.execute(query=f"update {table} set is_deleted=1 where created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
               if column.get("user_id",None):await postgres_client.execute(query=f"update {table} set is_deleted=1 where user_id=:user_id;",values={"user_id":request.state.user["id"]})
               if column.get("parent_table",None):await postgres_client.execute(query=f"update {table} set is_deleted=1 where parent_table={table_id.get('users')} and parent_id=:parent_id;",values={"parent_id":request.state.user["id"]})
         await postgres_client.execute(query="update users set is_deleted=1 where id=:id;",values={"id":request.state.user["id"]})
   if account_delete_mode=="hard":
      async with postgres_client.transaction():
         for table,column in postgres_schema.items():
            if table not in ["users"]:
               if column.get("created_by_id",None):await postgres_client.execute(query=f"delete from {table} where created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
               if column.get("user_id",None):await postgres_client.execute(query=f"delete from {table} where user_id=:user_id;",values={"user_id":request.state.user["id"]})
               if column.get("parent_table",None):await postgres_client.execute(query=f"delete from {table} where parent_table={table_id.get('users')} and parent_id=:parent_id;",values={"parent_id":request.state.user["id"]})
         await postgres_client.execute(query="update users set is_protected=null where id=:id;",values={"id":request.state.user["id"]})
         await postgres_client.execute(query="delete from users where id=:id;",values={"id":request.state.user["id"]})
   return {"status":1,"message":f"{account_delete_mode} deletion of user {request.state.user['id']} done"}

#message
@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   mode=query_param.get("mode",None)
   query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {(page-1)*limit};'''
   if mode=="unread":query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {(page-1)*limit};'''
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request,background:BackgroundTasks):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   user_id=query_param.get("user_id",None)
   if not user_id:return error("query param user_id missing")
   user_id=int(user_id)
   query=f"select * from message where ((created_by_id=:user_1 and user_id=:user_2) or (created_by_id=:user_2 and user_id=:user_1)) order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_1":request.state.user["id"],"user_2":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   background.add_task(postgres_client.execute,query="update message set is_read=1,updated_by_id=:updated_by_id where created_by_id=:created_by_id and user_id=:user_id;",values={"created_by_id":user_id,"user_id":request.state.user["id"],"updated_by_id":request.state.user["id"]})
   return {"status":1,"message":object_list}

@app.get("/my/message-received")
async def my_message_received(request:Request,background:BackgroundTasks):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   mode=query_param.get("mode",None)
   query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {(page-1)*limit};"
   if mode=="unread":query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   background.add_task(postgres_client.execute,query=f"update message set is_read=1,updated_by_id=:updated_by_id where id in ({','.join([str(item['id']) for item in object_list])});",values={"updated_by_id":request.state.user["id"]})
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete")
async def my_message_delete(request:Request):
   query_param=dict(request.query_params)
   mode,id=query_param.get("mode",None),query_param.get("id",None)
   if not mode:return error("query param mode missing")
   if mode=="single":
      if not id:return error("query param id missing")
      output=await postgres_client.execute(query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);",values={"id":int(id),"user_id":request.state.user["id"]})
   if mode=="created":output=await postgres_client.execute(query="delete from message where created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   if mode=="received":output=await postgres_client.execute(query="delete from message where user_id=:user_id;",values={"user_id":request.state.user["id"]})
   if mode=="all":output=await postgres_client.execute(query="delete from message where (created_by_id=:user_id or user_id=:user_id);",values={"user_id":request.state.user["id"]})
   return {"status":1,"message":output}

#action
@app.get("/my/action-parent-read")
async def my_action_parent_read(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   action_count=query_param.get("action_count",None)
   table,parent_table=query_param.get("table"),int(query_param.get("parent_table"))
   if not table or not parent_table:return error("query param table/parent_table missing")
   query=f'''with x as (select parent_id from {table} where created_by_id=:created_by_id and parent_table=:parent_table order by {order} limit {limit} offset {(page-1)*limit}) select pt.* from x left join {next((k for k,v in table_id.items() if v==parent_table), None)} as pt on x.parent_id=pt.id;'''
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table,}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   if action_count:
      for action_table in action_count.split(","):
         response=await add_action_count(postgres_client,action_table,object_list,table_id.get(parent_table))
         if response["status"]==0:return response
         object_list=response["message"]
   return {"status":1,"message":object_list}

@app.get("/my/action-parent-check")
async def my_action_parent_check(request:Request):
   query_param=dict(request.query_params)
   table,parent_table,parent_ids=query_param.get("table"),int(query_param.get("parent_table")),query_param.get("parent_ids")
   if not table or not parent_table or not parent_ids:return error("query param table/parent_table/parent_ids missing")
   query=f"select parent_id from {table} where parent_id in ({parent_ids}) and parent_table=:parent_table and created_by_id=:created_by_id;"
   query_param={"parent_table":parent_table,"created_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   parent_ids_output=[item["parent_id"] for item in output if item["parent_id"]]
   parent_ids_input=[int(item) for item in parent_ids.split(",")]
   output={id:1 if id in parent_ids_output else 0 for id in parent_ids_input}
   return {"status":1,"message":output}

@app.delete("/my/action-parent-delete")
async def my_action_parent_delete(request:Request):
   query_param=dict(request.query_params)
   table,parent_table,parent_id=query_param.get("table"),int(query_param.get("parent_table")),int(query_param.get("parent_id"))
   if not table or not parent_table or not parent_id:return error("body json table/parent_table/parent_id missing")
   if "action_" not in table:return error("table not allowed")
   await postgres_client.fetch_all(query=f"delete from {table} where created_by_id=:created_by_id and parent_table=:parent_table and parent_id=:parent_id;",values={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id})
   return {"status":1,"message":"done"}

@app.get("/my/action-on-me-creator-read")
async def my_action_on_me_creator_read(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   table=query_param.get("table")
   if not table:return error("query param table missing")
   query=f'''with x as (select * from {table} where parent_table=:parent_table),y as (select created_by_id from x where parent_id=:parent_id group by created_by_id order by max(id) desc limit {limit} offset {(page-1)*limit}) select u.id,u.username from y left join users as u on y.created_by_id=u.id;'''
   query_param={"parent_table":table_id.get('users',0),"parent_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/action-on-me-creator-read-mutual")
async def my_action_on_me_creator_read_mutual(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   table=query_param.get("table")
   if not table:return error("query param table missing")
   query=f'''with x as (select * from {table} where parent_table=:parent_table),y as (select created_by_id from {table} where created_by_id in (select parent_id from x where created_by_id=:created_by_id) and parent_id=:parent_id group by created_by_id order by max(id) desc limit {limit} offset {(page-1)*limit}) select u.id,u.username from y left join users as u on y.created_by_id=u.id;'''
   query_param={"parent_table":table_id.get('users',0),"parent_id":request.state.user["id"],"created_by_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

#object create
@app.post("/my/object-create")
async def my_object_create(request:Request):
   query_param=dict(request.query_params)
   is_serialize,queue=int(query_param.get("is_serialize",1)),query_param.get("queue",None)
   table=query_param.get("table")
   if not table:return error("query param table missing")
   if table in ["spatial_ref_sys","users","otp","log_api","log_password"]:return error("table not allowed")
   object=await request.json()
   object["created_by_id"]=request.state.user["id"]
   if len(object)<=1:return error ("object issue")
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   for key,value in object.items():
      if key in column_disabled_non_admin:return error(f"{key} not allowed")
   if not queue:
      response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
      if response["status"]==0:return error(response["message"])
      output=response["message"]
   if queue:
      data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
      if queue=="redis":output=await redis_client.publish(channel_name,json.dumps(data))
      if queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
      if queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
      if queue=="kafka":output=await kafka_producer_client.send_and_wait(channel_name,json.dumps(data,indent=2).encode('utf-8'),partition=0)
      if "mongodb" in queue:
         mongodb_database_name=queue.split("_")[1]
         mongodb_database_client=mongodb_client[mongodb_database_name]
         output=await mongodb_database_client[table].insert_many([object])
         output=str(output)
   return {"status":1,"message":output}

@app.post("/public/object-create")
async def public_object_create(request:Request):
   query_param=dict(request.query_params)
   is_serialize=int(query_param.get("is_serialize",1))
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if table not in ["test","helpdesk","human"]:return error("table not allowed")
   object=await request.json()
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   for key,value in object.items():
      if key in column_disabled_non_admin:return error(f"{key} not allowed")
   response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   return response

@app.post("/root/object-create")
async def root_object_create(request:Request):
   query_param=dict(request.query_params)
   is_serialize=int(query_param.get("is_serialize",1))
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if table in ["spatial_ref_sys"]:return error("table not allowed")
   object=await request.json()
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   for key,value in object.items():
      if key in column_lowercase:object[key]=value.strip().lower()
   if "password" in object:is_serialize=1
   response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   return response

#object read
@app.get("/my/object-read")
@cache(expire=60)
async def my_object_read(request:Request):
   query_param=dict(request.query_params)
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   query_param["created_by_id"]=f"=,{request.state.user['id']}"
   response=await postgres_read(table,query_param,postgres_client,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count,table_id)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/public/object-read")
@cache(expire=60)
async def public_object_read(request:Request):
   query_param=dict(request.query_params)
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if table not in ["post","atom"]:return error("table not allowed")
   response=await postgres_read(table,query_param,postgres_client,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count,table_id)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/admin/object-read")
@cache(expire=60)
async def admin_object_read(request:Request):
   query_param=dict(request.query_params)
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   response=await postgres_read(table,query_param,postgres_client,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count,table_id)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/private/object-read")
@cache(expire=60)
async def private_object_read(request:Request):
   query_param=dict(request.query_params)
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if table not in ["post","atom","human"]:return error("table not allowed")
   response=await postgres_read(table,query_param,postgres_client,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count,table_id)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/private/human-read")
@cache(expire=100)
async def private_human_read(request:Request):
   #query param
   query_param=dict(request.query_params)
   column=query_param.get("column","*")
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   type,work_profile,skill=query_param.get("type"),query_param.get("work_profile"),query_param.get("skill")
   experience_min,experience_max=query_param.get("experience_min"),query_param.get("experience_max")
   rating_min,rating_max=query_param.get("rating_min"),query_param.get("rating_max")
   #none conversion
   char_disabled=["","null","%%"]
   if type in char_disabled:type=None
   if work_profile in char_disabled:work_profile=None
   if skill in char_disabled:skill=None
   if experience_min in char_disabled:experience_min=None
   if experience_max in char_disabled:experience_max=None
   if rating_min in char_disabled:rating_min=None
   if rating_max in char_disabled:rating_max=None
   #datatype conversion
   if experience_min:experience_min=float(experience_min)
   if experience_max:experience_max=float(experience_max)
   if rating_min:rating_min=float(rating_min)
   if rating_max:rating_max=float(rating_max)
   #query set
   query=f'''
   select {column} from human 
   where is_active=1 and
   type in ('jobseeker','intern','freelancer','consultant') and
   (work_profile ilike :work_profile or :work_profile is null) and
   (skill ilike :skill or :skill is null) and
   (experience >= :experience_min or :experience_min is null) and
   (experience <= :experience_max or :experience_max is null) and
   (rating >= :rating_min or :rating_min is null) and
   (rating <= :rating_max or :rating_max is null)
   order by {order} limit {limit} offset {(page-1)*limit};
   '''
   query_param={
   "work_profile":work_profile,
   "skill":skill,
   "experience_min":experience_min,"experience_max":experience_max,
   "rating_min":rating_min,"rating_max":rating_max,
   }
   #query run
   output=await postgres_client.fetch_all(query=query,values=query_param)
   #final
   return {"status":1,"message":output}

#object update
@app.put("/my/object-update")
async def my_object_update(request:Request):
   query_param=dict(request.query_params)
   is_serialize,otp=int(query_param.get("is_serialize",1)),int(query_param.get("otp",0))
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if table in ["spatial_ref_sys","otp","log_api","log_password"]:return error("table not allowed")
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   if len(object)<=2:return error ("object issue")
   if "id" not in object:return error ("id missing")
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   for key,value in object.items():
      if key in column_disabled_non_admin:return error(f"{key} not allowed")
   if "password" in object:is_serialize=1
   if "password" in object and len(object)!=3:return error("object length should be 2 only")
   if "email" in object and table=="users" and len(object)!=3:return error("object length should be 2 only")
   if "mobile" in object and table=="users" and len(object)!=3:return error("object length should be 2 only")
   response=await ownership_check(postgres_client,table,int(object["id"]),request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   email,mobile=object.get("email",None),object.get("mobile",None)
   if table=="users" and (email or mobile):
      if not otp:return error("query param otp missing")
      response=await verify_otp(postgres_client,otp,email,mobile)
      if response["status"]==0:return error(response["message"])
   response=await postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   return response

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   query_param=dict(request.query_params)
   is_serialize=int(query_param.get("is_serialize",1))
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if table in ["spatial_ref_sys"]:return error("table not allowed")
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   if len(object)<=2:return error ("object issue")
   if "id" not in object:return error ("id missing")
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   if "password" in object and len(object)!=3:return error("object length should be 2 only")
   if "password" in object:is_serialize=1
   response=await postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   return response

@app.put("/root/object-update")
async def root_object_update(request:Request):
   query_param=dict(request.query_params)
   is_serialize=int(query_param.get("is_serialize",1))
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if table in ["spatial_ref_sys"]:return error("table not allowed")
   object=await request.json()
   if len(object)<=1:return error ("object issue")
   if "id" not in object:return error ("id missing")
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   if "password" in object and len(object)!=2:return error("object length should be 2 only")
   if "password" in object:is_serialize=1
   response=await postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   return response

#object delete
@app.delete("/my/object-delete")
async def my_object_delete(request:Request):
   query_param=dict(request.query_params)
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   if "action_" not in table:return error("table not allowed")
   query_param["created_by_id"]=f"=,{request.state.user['id']}"
   response=await create_where_string(postgres_column_datatype,object_serialize,query_param)
   if response["status"]==0:return error(response["message"])
   where_string,where_value=response["message"][0],response["message"][1]
   query=f"delete from {table} {where_string};"
   await postgres_client.fetch_all(query=query,values=where_value)
   return {"status":1,"message":"done"}

#ids
@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   body_json=await request.json()
   table,ids,column,value=body_json.get("table"),body_json.get("ids"),body_json.get("column"),body_json.get("value")
   if not table or not ids or not column:return error("body json table/ids/column must")
   if table in ["spatial_ref_sys","users","otp","log_api","log_password"]:return error("table not allowed")
   object={column:value}
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   for key,value in object.items():
      if key in column_disabled_non_admin:return error(f"{key} not allowed")
   response=await object_serialize(postgres_column_datatype,[object])
   if response["status"]==0:return response
   object=response["message"][0]
   await postgres_client.execute(query=f"update {table} set {column}=:value,updated_by_id=:updated_by_id where id in ({ids}) and created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"],"updated_by_id":request.state.user["id"],"value":object.get(column)})
   return {"status":1,"message":"done"}
 
@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   body_json=await request.json()
   table,ids,column,value=body_json.get("table"),body_json.get("ids"),body_json.get("column"),body_json.get("value")
   if not table or not ids or not column:return error("body json table/ids/column must")
   if table in ["spatial_ref_sys"]:return error("table not allowed")
   object={column:value}
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   response=await object_serialize(postgres_column_datatype,[object])
   if response["status"]==0:return response
   object=response["message"][0]
   await postgres_client.execute(query=f"update {table} set {column}=:value,updated_by_id=:updated_by_id where id in ({ids});",values={"updated_by_id":request.state.user["id"],"value":object.get(column)})
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   body_json=await request.json()
   table,ids=body_json.get("table"),body_json.get("ids")
   if not table or not ids:return error("body json table/ids must")
   if table in ["spatial_ref_sys","users"]:return error("table not allowed")
   if len(ids.split(","))>max_ids_length_delete:return error("ids length not allowed")
   await postgres_client.execute(query=f"delete from {table} where id in ({ids}) and created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   body_json=await request.json()
   table,ids=body_json.get("table"),body_json.get("ids")
   if not table or not ids:return error("body json table/ids must")
   if table in ["spatial_ref_sys","users"]:return error("table not allowed")
   if len(ids.split(","))>max_ids_length_delete:return error("ids length not allowed")
   await postgres_client.execute(query=f"delete from {table} where id in ({ids});",values={})
   return {"status":1,"message":"done"}

#public
@app.get("/public/info")
async def public_info(request:Request):
   global output_cache_info
   if not output_cache_info or (time.time()-output_cache_info.get("set_at")>60):
      output_cache_info={
      "set_at":time.time(),
      "users_api_access_count":len(users_api_access),
      "users_is_active_count":len(users_is_active),
      "postgres_column_datatype":postgres_column_datatype,
      "postgres_schema":postgres_schema,
      "api_list":[route.path for route in request.app.routes],
      "redis":await redis_client.info(),
      "table_id":table_id,
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True)),
      "mission":await postgres_client.fetch_all(query="select count(*) from human where is_active=1;",values={}),
      "human_work_profile":await postgres_client.fetch_all(query=query_human_work_profile,values={}),
      "human_skill":await postgres_client.fetch_all(query=query_human_skill,values={})
      }
   return {"status":1,"message":output_cache_info}

#otp
@app.post("/public/otp-send-sns")
async def public_otp_send_sns(request:Request):
   body_json=await request.json()
   mobile=body_json.get("mobile")
   entity_id,sender_id,template_id,message=body_json.get("entity_id",None),body_json.get("sender_id",None),body_json.get("template_id",None),body_json.get("message",None)
   if not mobile:return error("body json mobile missing")
   mobile=mobile.strip().lower()
   otp=random.randint(100000,999999)
   await postgres_client.execute(query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;",values={"otp":otp,"mobile":mobile})
   if not entity_id:output=sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   else:output=sns_client.publish(PhoneNumber=mobile,Message=message.replace("{otp}",str(otp)),MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return {"status":1,"message":output}

@app.post("/public/otp-send-ses")
async def public_otp_send_ses(request:Request):
   body_json=await request.json()
   email,sender=body_json.get("email"),body_json.get("sender")
   if not email or not sender:return error("body json email/sender missing")
   email=email.strip().lower()
   otp=random.randint(100000,999999)
   await postgres_client.fetch_all(query="insert into otp (otp,email) values (:otp,:email) returning *;",values={"otp":otp,"email":email})
   to,title,body=[email],"otp from atom",str(otp)
   ses_client.send_email(Source=sender,Destination={"ToAddresses":to},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return {"status":1,"message":"done"}

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
   await set_postgres_client()
   await set_postgres_schema()
   await set_redis_client()
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
      await redis_pubsub.unsubscribe("postgres_crud")
      await redis_client.aclose()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="redis":
    try:asyncio.run(main_redis())
    except KeyboardInterrupt:print("exit")

#kafka
import asyncio,json
async def main_kafka():
   await set_postgres_client()
   await set_postgres_schema()
   await set_kafka_client()
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_rabbitmq_client()
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_lavinmq_client()
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