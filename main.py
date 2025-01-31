#env
import os
from dotenv import load_dotenv
load_dotenv()

#function
async def postgres_crud(mode,table,object_list,is_serialize,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count):
   #check
   if not object_list:return {"status":0,"message":"object null issue"}
   if not postgres_schema.get(table,None):return {"status":0,"message":"table not allowed"}
   if mode!="read":
      for k,v in object_list[0].items():
         if k not in postgres_schema.get(table,{}):return {"status":0,"message":f"column {k} not in {table}"}
         if k=="parent_table" and not postgres_schema.get(v,None):return {"status":0,"message":"parent_table not allowed"}
   #serialize
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   #create
   if mode=="create":
      column_insert_list=[*object_list[0]]
      query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   #read
   if mode=="read":
      object=object_list[0]
      order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
      location_filter=object.get("location_filter",None)
      is_creator_data,action_count=object.get("is_creator_data",None),object.get("action_count",None)
      response=await create_where_string(postgres_column_datatype,object_serialize,object)
      if response["status"]==0:return response
      where_string,where_value=response["message"][0],response["message"][1]
      query=f"select * from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
      if location_filter:
         long,lat,min_meter,max_meter=float(location_filter.split(",")[0]),float(location_filter.split(",")[1]),int(location_filter.split(",")[2]),int(location_filter.split(",")[3])
         query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
      query_param=where_value
      object_list=await postgres_client.fetch_all(query=query,values=query_param)
      if is_creator_data=="1":
         response=await add_creator_data(postgres_client,object_list)
         if response["status"]==0:return response
         object_list=response["message"]
      if action_count:
         for item in action_count.split(","):
            response=await add_action_count(postgres_client,f"action_{item}",table,object_list)
            if response["status"]==0:return response
            object_list=response["message"]
      return {"status":1,"message":object_list}
   #update
   if mode=="update":
      column_update_list=[*object_list[0]]
      column_update_list.remove("id")
      query=f"update {table} set {','.join([f'{item}=coalesce(:{item},{item})' for item in column_update_list])} where id=:id returning *;"
   #delete
   if mode=="delete":
      query=f"delete from {table} where id=:id;"
   #query run
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
   #final
   return {"status":1,"message":output}

async def postgres_transaction(postgres_client,query_list):
   transaction=await postgres_client.transaction()
   try:
      output=[await postgres_client.fetch_all(query=query,values={}) for query in query_list]
   except Exception as e:
      await transaction.rollback()
      return {"status":0,"message":e.args}
   else:
      await transaction.commit()
   return {"status":1,"message":output}

async def postgres_schema_init(postgres_client,config):
   postgres_schema={}
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"],"nullable":object["is_nullable"],"default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''',values={})]
   index_name_list=[object["indexname"] for object in (await postgres_client.fetch_all(query="select indexname from pg_indexes where schemaname='public';",values={}))]
   constraint_name_list=[object["constraint_name"] for object in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))]
   for query in config["query"]["extension"].split("---"):await postgres_client.fetch_all(query=query,values={})
   for table,v in config["table"].items():
      if table not in postgres_schema:await postgres_client.execute(f"create table if not exists {table} (id bigint primary key generated always as identity not null);",values={})
      for column in v:
         column=column.split("-")
         if not postgres_schema.get(table,{}).get(column[0],None):await postgres_client.execute(f"alter table {table} add column if not exists {column[0]} {column[1]};",values={})
         [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''',values={})]
         if column[2]=="1" and postgres_schema.get(table,{}).get(column[0],{}).get("nullable")=="YES":await postgres_client.execute(f"alter table {table} alter column {column[0]} set not null;",values={})
         if column[3]!="0" and f"index_{table}_{column[0]}" not in index_name_list:await postgres_client.execute(query=f"create index concurrently if not exists index_{table}_{column[0]} on {table} using {column[3]} ({column[0]});",values={})
   for k,v in config["query"].items():
      for query in v.split("---"):
         if "add constraint" in query and query.split()[5] in constraint_name_list:continue
         await postgres_client.fetch_all(query=query,values={})
   return {"status":1,"message":"done"}

async def postgres_clean_creator(postgres_client):
   postgres_schema={}
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''',values={})]
   for table,column in postgres_schema.items():
      if column.get("created_by_id",None):
         query=f"delete from {table} where created_by_id not in (select id from users);"
         await postgres_client.execute(query=query,values={})
   return {"status":1,"message":"done"}

async def postgres_clean_parent(postgres_client):
   postgres_schema={}
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''',values={})]
   for table,column in postgres_schema.items():
      if column.get("parent_table",None) and column.get("parent_id",None):
         output=await postgres_client.fetch_all(query=f"select distinct(parent_table) from {table};",values={})
         parent_table_list=[item['parent_table'] for item in output]
         for parent_table in parent_table_list:
            if parent_table not in postgres_schema:return {"status":0,"message":f"{table} has invalid parent_table {parent_table} "}
            query=f"delete from {table} where parent_table='{parent_table}' and parent_id not in (select id from {parent_table});"
            await postgres_client.execute(query=query,values={})
   return {"status":1,"message":"done"}

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

import hashlib,datetime,json
async def object_serialize(postgres_column_datatype,object_list):
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

async def create_where_string(postgres_column_datatype,object_serialize,object):
   object={k:v for k,v in object.items() if k in postgres_column_datatype}
   object={k:v for k,v in object.items() if k not in ["metadata","location","table","order","limit","page"]}
   object_key_operator={k:v.split(',',1)[0] for k,v in object.items()}
   object_key_value={k:v.split(',',1)[1] for k,v in object.items()}
   column_read_list=[*object]
   where_column_single_list=[f"({column} {object_key_operator[column]} :{column} or :{column} is null)" for column in column_read_list]
   where_column_joined=' and '.join(where_column_single_list)
   where_string=f"where {where_column_joined}" if where_column_joined else ""
   response=await object_serialize(postgres_column_datatype,[object_key_value])
   if response["status"]==0:return response
   where_value=response["message"][0]
   return {"status":1,"message":[where_string,where_value]}

import uuid
async def s3_file_upload(s3_client,s3_region_name,bucket,key_list,file_list):
   if not key_list:key_list=[f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}" for file in file_list]
   output={}
   for index,file in enumerate(file_list):
      key=key_list[index]
      if "." not in key:return {"status":0,"message":"extension must"}
      file_content=await file.read()
      file_size_kb=round(len(file_content)/1024)
      if file_size_kb>100:return {"status":0,"message":f"{file.filename} has {file_size_kb} kb size which is not allowed"}
      file_stream=BytesIO(file_content)
      s3_client.upload_fileobj(file_stream,bucket,key)
      output[file.filename]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
      file.file.close()
   return {"status":1,"message":output}

#globals env
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
sns_region_name=os.getenv("sns_region_name")
ses_region_name=os.getenv("ses_region_name")
mongodb_cluster_url=os.getenv("mongodb_cluster_url")

#globals custom
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
"atom":["type-text-1-btree","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0","parent_table-text-0-btree","parent_id-bigint-0-btree"],
"project":["type-text-1-btree","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0"],
"users":["created_at-timestamptz-1-brin","updated_at-timestamptz-0-0","updated_by_id-bigint-0-0","is_active-smallint-0-btree","is_protected-smallint-0-btree","type-text-0-btree","username-text-0-0","password-text-0-btree","location-geography(POINT)-0-gist","metadata-jsonb-0-0","google_id-text-0-btree","last_active_at-timestamptz-0-0","date_of_birth-date-0-0","email-text-0-btree","mobile-text-0-btree","name-text-0-0","city-text-0-0"],
"post":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","updated_at-timestamptz-0-0","updated_by_id-bigint-0-0","type-text-0-0","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0","location-geography(POINT)-0-0","metadata-jsonb-0-0"],
"message":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","user_id-bigint-1-btree","description-text-1-0","is_read-smallint-0-btree"],
"helpdesk":["created_at-timestamptz-1-0","created_by_id-bigint-0-0","status-text-0-0","remark-text-0-0","type-text-0-0","description-text-1-0","email-text-0-btree"],
"otp":["created_at-timestamptz-1-brin","otp-integer-1-0","email-text-0-btree","mobile-text-0-btree"],
"log_api":["created_at-timestamptz-1-0","created_by_id-bigint-0-0","api-text-0-0","status_code-smallint-0-0","response_time_ms-numeric(1000,3)-0-0"],
"log_password":["created_at-timestamptz-1-0","user_id-bigint-0-0","password-text-0-0"],
"action_like":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_bookmark":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_report":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_block":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_follow":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_rating":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","rating-numeric(10,3)-1-0"],
"action_comment":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","description-text-1-0"],
"human":["created_at-timestamptz-1-0","type-text-0-btree","name-text-0-0","email-text-0-0","mobile-text-0-0","city-text-0-0","experience-numeric(10,1)-0-0","link_url-text-0-0","work_profile-text-0-0","skill-text-0-0","description-text-0-0","file_url-text-0-0"],
},
"query":{
"default_created_at":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'created_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"default_updated_at":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';---DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'updated_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected = 1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"root_user":"insert into users (type,username,password) values ('admin','atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3') on conflict do nothing;---create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"log_password":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;---CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"extension":"create extension if not exists postgis;",
"delete_disable_bulk":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;---create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
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
   [postgres_schema.setdefault(object["table_name"],{}).update({object["column_name"]:{"datatype":object["data_type"], "nullable":object["is_nullable"], "default":object["column_default"]}}) for object in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''',values={})]
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return None

async def set_users_type_ids():
   global users_type_ids
   users_type_ids={}
   for type in ["admin"]:
      users_type_ids[type]=[]
      output=await postgres_client.fetch_all(query="select id from users where type=:type limit 10000",values={"type":type})
      for object in output:users_type_ids[type]+=[object["id"]]
   return None

async def set_project_data():
   global project_data
   project_data={}
   output=await postgres_client.fetch_all(query="select * from project limit 10000;",values={})
   for object in output:
      if object["type"] not in project_data:project_data[object["type"]]=[object]
      else:project_data[object["type"]]+=[object]
   return None

import redis.asyncio as redis
async def set_redis_client():
   global redis_client,redis_pubsub
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(os.getenv("redis_server_url")))
   redis_pubsub=redis_client.pubsub()
   await redis_pubsub.subscribe("postgres_crud")
   return None

import boto3
async def set_aws_client():
   global s3_client,s3_resource,sns_client,ses_client
   if s3_region_name:
      s3_client=boto3.client("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   if s3_region_name:
      s3_resource=boto3.resource("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   if sns_region_name:
      sns_client=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   if ses_region_name:
      ses_client=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
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
      rabbitmq_channel.queue_declare(queue="postgres_crud")
   return None

import pika
async def set_lavinmq_client():
   global lavinmq_client,lavinmq_channel
   if lavinmq_server_url:
      lavinmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("lavinmq_server_url")))
      lavinmq_channel=lavinmq_client.channel()
      lavinmq_channel.queue_declare(queue="postgres_crud")
   return None

from aiokafka import AIOKafkaProducer
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def set_kafka_client():
   global kafka_producer_client,kafka_consumer_client
   if kafka_server_url:
      context=create_ssl_context(cafile=os.getenv("kafka_path_cafile"),certfile=os.getenv("kafka_path_certfile"),keyfile=os.getenv("kafka_path_keyfile"))
      kafka_producer_client=AIOKafkaProducer(bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context)
      kafka_consumer_client=AIOKafkaConsumer("postgres_crud",bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_users_type_ids()
   await set_project_data()
   await set_redis_client()
   await set_aws_client()
   await set_mongodb_client()
   await set_rabbitmq_client()
   await set_lavinmq_client()
   await set_kafka_client()
   await FastAPILimiter.init(redis_client)
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   yield
   try:
      await postgres_client.disconnect()
      await redis_client.aclose()
      if rabbitmq_server_url and rabbitmq_channel.is_open:rabbitmq_channel.close()
      if rabbitmq_client.is_open:rabbitmq_client.close()
      if lavinmq_server_url and lavinmq_channel.is_open:lavinmq_channel.close()
      if lavinmq_client.is_open:lavinmq_client.close()
      if kafka_server_url:await kafka_producer_client.stop()
   except Exception as e:print("app closed")

#app
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
   auth_header=request.headers.get("Authorization")
   token=auth_header.split("Bearer ",1)[1] if auth_header and "Bearer " in auth_header else None
   try:
      #auth
      user={}
      if any(item in api for item in ["root/","my/", "private/", "admin/"]) and not token:return responses.JSONResponse(status_code=400,content={"status":0,"message":"token must"})
      if token:
         if "root/" in api:
            if token!=key_root:return responses.JSONResponse(status_code=400,content={"status":0,"message":"root key mismatch"})
         else:
            user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
            if not user.get("id",None):return responses.JSONResponse(status_code=400,content={"status":0,"message":"wrong token"})
            if "admin/" in api and user["id"] not in users_type_ids.get("admin",[]):return responses.JSONResponse(status_code=400,content={"status":0,"message":"only admin allowed"})
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
         #api log
         if "log_api" in postgres_schema:
            global object_list_log
            object={"created_by_id":user.get("id",None),"api":api,"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000}
            object_list_log.append(object)
            if len(object_list_log)>=3:
               response.background=BackgroundTask(postgres_crud,"create","log_api",object_list_log,0,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
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
      
#import
from fastapi import Request,UploadFile,responses,Depends,BackgroundTasks,File,Form
import hashlib,datetime,json,time,jwt,csv,codecs,os,random,uuid
from io import BytesIO
from typing import Literal
from bson.objectid import ObjectId
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from PyPDF2 import PdfReader
import fitz

#index
@app.get("/")
async def root():
   return {"status":1,"message":"welcome to atom"}
   
#root
@app.post("/root/schema-init")
async def root_schema_init(request:Request,mode:str=None):
   if not mode:config=postgres_config_default
   if mode=="custom":config=await request.json()
   await postgres_schema_init(postgres_client,config)
   return {"status":1,"message":"done"}

@app.get("/root/info")
async def root_info(request:Request):
   globals_dict=globals()
   output={
   "users_type_ids":users_type_ids,
   "project_data":project_data,
   "postgres_schema":postgres_schema,
   "api_list":[route.path for route in request.app.routes],
   "api_count":len([route.path for route in request.app.routes]),
   "redis":await redis_client.info(),
   "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals_dict.items() if not name.startswith("__")}.items(), key=lambda item: item[1], reverse=True))
   }
   return {"status":1,"message":output}

@app.get("/root/reset-global")
async def root_reset_global():
   await set_postgres_schema()
   await set_project_data()
   await set_users_type_ids()
   return {"status":1,"message":"done"}

@app.get("/root/reset-redis")
async def root_reset_redis():
   await redis_client.flushall()
   return {"status":1,"message":"done"}

@app.get("/root/clean")
async def root_clean():
   response=await postgres_clean_creator(postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   response=await postgres_clean_parent(postgres_client)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   await postgres_client.execute(query="truncate table log_api;",values={})
   return {"status":1,"message":"done"}

@app.get("/root/checklist")
async def root_checklist():
   await postgres_client.execute(query="update users set is_protected=1 where type='admin';",values={})
   return {"status":1,"message":"done"}

@app.get("/root/query-runner")
async def root_query_runner(query:str):
   response=await postgres_transaction(postgres_client,query.split("---"))
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.post("/root/postgres-crud-csv")
async def root_postgres_crud_csv(mode:str,table:str,file:UploadFile):
   object_list=[row for row in csv.DictReader(codecs.iterdecode(file.file,'utf-8'))]
   file.file.close()
   response=await postgres_crud(mode,table,object_list,1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.get("/root/s3-bucket-list")
async def root_s3_bucket_list():
   output=s3_client.list_buckets()
   return {"status":1,"message":output}

@app.get("/root/s3-bucket-create")
async def root_s3_bucket_create(bucket:str):
   output=s3_client.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})
   return {"status":1,"message":output}

@app.get("/root/s3-bucket-public")
async def root_s3_bucket_public(bucket:str):
   s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal": "*","Action": "s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return {"status":1,"message":output}

@app.get("/root/s3-bucket-empty")
async def root_s3_bucket_empty(bucket:str):
   output=s3_resource.Bucket(bucket).objects.all().delete()
   return {"status":1,"message":output}

@app.get("/root/s3-bucket-delete")
async def root_s3_bucket_empty(bucket:str):
   output=s3_client.delete_bucket(Bucket=bucket)
   return {"status":1,"message":output}

@app.get("/root/s3-url-delete")
async def root_s3_url_empty(url:str):
   for item in url.split("---"):
      bucket,key=item.split("//",1)[1].split(".",1)[0],item.rsplit("/",1)[1]
      output=s3_resource.Object(bucket,key).delete()
   return {"status":1,"message":output}

@app.post("/root/redis-set-object")
async def root_redis_set_object(request:Request,key:str,expiry:int=None):
   object=await request.json()
   object=json.dumps(object)
   if expiry:output=await redis_client.setex(key,expiry,object)
   else:output=await redis_client.set(key,object)
   return {"status":1,"message":output}

@app.post("/root/redis-set-csv")
async def root_redis_set_csv(table:str,file:UploadFile,expiry:int=None):
   object_list=[row for row in csv.DictReader(codecs.iterdecode(file.file,'utf-8'))]
   file.file.close()
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if expiry:pipe.setex(key,expiry,json.dumps(object))
         else:pipe.set(key,json.dumps(object))
      await pipe.execute()
   return {"status":1,"message":"done"}

#auth
@app.get("/auth/signup",dependencies=[Depends(RateLimiter(times=1,seconds=3))])
async def auth_signup(username:str,password:str):
   query="insert into users (username,password) values (:username,:password) returning *;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.get("/auth/login")
async def auth_login(username:str,password:str):
   output=await postgres_client.fetch_all(query="select id from users where username=:username and password=:password order by id desc limit 1;",values={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()})
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/auth/login-google")
async def auth_login_google(google_id:str):
   output=await postgres_client.fetch_all(query="select id from users where google_id=:google_id order by id desc limit 1;",values={"google_id":hashlib.sha256(google_id.encode()).hexdigest()})
   if not output:output=await postgres_client.fetch_all(query="insert into users (google_id) values (:google_id) returning *;",values={"google_id":hashlib.sha256(google_id.encode()).hexdigest()})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/auth/login-otp-email")
async def auth_login_otp_email(otp:int,email:str):
   response=await verify_otp(postgres_client,otp,email,None)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   output=await postgres_client.fetch_all(query="select id from users where email=:email order by id desc limit 1;",values={"email":email})
   if not output:output=await postgres_client.fetch_all(query="insert into users (email) values (:email) returning *;",values={"email":email})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/auth/login-otp-mobile")
async def auth_login_otp_mobile(otp:int,mobile:str):
   response=await verify_otp(postgres_client,otp,None,mobile)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   output=await postgres_client.fetch_all(query="select id from users where mobile=:mobile order by id desc limit 1;",values={"mobile":mobile})
   if not output:output=await postgres_client.fetch_all(query="insert into users (mobile) values (:mobile) returning *;",values={"mobile":mobile})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/auth/login-password-email")
async def auth_login_password_email(password:str,email:str):
   output=await postgres_client.fetch_all(query="select * from users where email=:email and password=:password order by id desc limit 1;",values={"email":email,"password":hashlib.sha256(password.encode()).hexdigest()})
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/auth/login-password-mobile")
async def auth_login_password_mobile(password:str,mobile:str):
   output=await postgres_client.fetch_all(query="select * from users where mobile=:mobile and password=:password order by id desc limit 1;",values={"mobile":mobile,"password":hashlib.sha256(password.encode()).hexdigest()})
   if not output:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

#my
@app.get("/my/profile")
async def my_profile(request:Request,background:BackgroundTasks):
   user=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   background.add_task(postgres_client.execute,query="update users set last_active_at=:last_active_at where id=:id",values={"id":request.state.user["id"],"last_active_at":datetime.datetime.now()})
   return {"status":1,"message":user[0]}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":request.state.user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/my/object-create")
async def my_object_create(request:Request,table:str,is_serialize:int=0,queue:str=None):
   object=await request.json()
   object={k:v for k,v in object.items() if v}
   if any(k in ["id","created_at","updated_at","updated_by_id","is_active","is_verified","is_deleted","password","google_id","otp"] for k in object):return responses.JSONResponse(status_code=400,content={"status":0,"message":"key denied"})
   object["created_by_id"]=request.state.user["id"]
   if not queue:
      response=await postgres_crud("create",table,[object],is_serialize,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      output=response["message"]
   if queue:
      data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
      channel="postgres_crud"
      if queue=="redis":output=await redis_client.publish(channel,json.dumps(data))
      if queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=channel,body=json.dumps(data))
      if queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=channel,body=json.dumps(data))
      if queue=="kafka":output=await kafka_producer_client.send_and_wait(channel,json.dumps(data,indent=2).encode('utf-8'),partition=0)
      if "mongodb" in queue:
         mongodb_database_name=queue.split("_")[1]
         mongodb_database_client=mongodb_client[mongodb_database_name]
         output=await mongodb_database_client[table].insert_many([object])
         output=str(output)
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request,table:str,otp:int=None):
   object=await request.json()
   if any(k in ["created_at","created_by_id","is_active","is_verified","type","google_id","otp"] for k in object):return responses.JSONResponse(status_code=400,content={"status":0,"message":f"key denied"})      
   if postgres_schema.get(table,{}).get("updated_by_id",None):object["updated_by_id"]=request.state.user["id"]
   response=await ownership_check(postgres_client,table,int(object["id"]),request.state.user["id"])
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   email,mobile=object.get("email",None),object.get("mobile",None)
   if table=="users" and (email or mobile):
      response=await verify_otp(postgres_client,otp,email,mobile)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   response=await postgres_crud("update",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   output=response["message"]
   return {"status":1,"message":output}

@app.get("/my/object-read")
@cache(expire=60)
async def my_object_read(request:Request,table:str):
   object=dict(request.query_params)
   object["created_by_id"]=f"=,{request.state.user['id']}"
   response=await postgres_crud("read",table,[object],0,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.get("/my/message-inbox")
@cache(expire=60)
async def my_message_inbox(request:Request,mode:str=None):
   object=dict(request.query_params)
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {(page-1)*limit};'''
   if mode=="unread":query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {(page-1)*limit};'''
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/message-received")
@cache(expire=60)
async def my_message_received(request:Request,background:BackgroundTasks,mode:str=None):
   object=dict(request.query_params)
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {(page-1)*limit};"
   if mode=="unread":query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   background.add_task(postgres_client.execute,query=f"update message set is_read=1 where id in ({','.join([str(item['id']) for item in object_list])});",values={})
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
@cache(expire=60)
async def my_message_thread(request:Request,background:BackgroundTasks,user_id:int):
   object=dict(request.query_params)
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   query=f"select * from message where ((created_by_id=:user_1 and user_id=:user_2) or (created_by_id=:user_2 and user_id=:user_1)) order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_1":request.state.user["id"],"user_2":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   background.add_task(postgres_client.execute,query="update message set is_read=1 where created_by_id=:created_by_id and user_id=:user_id;",values={"created_by_id":user_id,"user_id":request.state.user["id"]})
   return {"status":1,"message":object_list}

@app.get("/my/parent-read")
@cache(expire=60)
async def my_parent_read(request:Request,table:str,parent_table:str):
   object=dict(request.query_params)
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   query=f'''with x as (select parent_id from {table} where created_by_id=:created_by_id and parent_table=:parent_table order by {order} limit {limit} offset {(page-1)*limit}) select pt.* from x left join {parent_table} as pt on x.parent_id=pt.id;'''
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/parent-check")
async def my_parent_check(request:Request,table:str,parent_table:str,parent_ids:str):
   query=f"select parent_id from {table} where parent_id in ({parent_ids}) and parent_table=:parent_table and created_by_id=:created_by_id;"
   query_param={"parent_table":parent_table,"created_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   parent_ids_output=[item["parent_id"] for item in output if item["parent_id"]]
   parent_ids_input=parent_ids.split(",")
   parent_ids_input=[int(item) for item in parent_ids_input]
   output={item:1 if item in parent_ids_output else 0 for item in parent_ids_input}
   return {"status":1,"message":output}

@app.get("/my/parent-delete")
async def my_parent_delete(request:Request,table:str,parent_table:str,parent_id:int):
   await postgres_client.fetch_all(query=f"delete from {table} where created_by_id=:created_by_id and parent_table=:parent_table and parent_id=:parent_id;",values={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id})
   return {"status":1,"message":"done"}

@app.get("/my/action-on-me-creator-read")
@cache(expire=60)
async def my_action_on_me_creator_read(request:Request,table:str):
   object=dict(request.query_params)
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   query=f'''with x as (select * from {table} where parent_table=:parent_table),y as (select created_by_id from x where parent_id=:parent_id group by created_by_id order by max(id) desc limit {limit} offset {(page-1)*limit}) select u.id,u.username from y left join users as u on y.created_by_id=u.id;'''
   query_param={"parent_table":"users","parent_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/action-on-me-creator-read-mutual")
@cache(expire=60)
async def my_action_on_me_creator_read_mutual(request:Request,table:str):
   object=dict(request.query_params)
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   query=f'''with x as (select * from {table} where parent_table=:parent_table),y as (select created_by_id from {table} where created_by_id in (select parent_id from x where created_by_id=:created_by_id) and parent_id=:parent_id group by created_by_id order by max(id) desc limit {limit} offset {(page-1)*limit}) select u.id,u.username from y left join users as u on y.created_by_id=u.id;'''
   query_param={"parent_table":"users","parent_id":request.state.user["id"],"created_by_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/message-delete-single")
async def my_message_delete_single(request:Request,id:int):
   await postgres_client.execute(query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);",values={"id":id,"user_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/message-delete-created")
async def my_message_delete_created(request:Request):
   await postgres_client.execute(query="delete from message where created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/message-delete-received")
async def my_message_delete_received(request:Request):
   await postgres_client.execute(query="delete from message where user_id=:user_id;",values={"user_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/message-delete-all")
async def my_message_delete_all(request:Request):
   await postgres_client.execute(query="delete from message where (created_by_id=:user_id or user_id=:user_id);",values={"user_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/delete-ids")
async def my_delete_ids(request:Request,table:str,ids:str):
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if len(ids.split(","))>100:return responses.JSONResponse(status_code=400,content={"status":0,"message":"max 100 ids allowed"})
   await postgres_client.execute(query=f"delete from {table} where id in ({ids}) and created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/delete-account")
async def my_delete_account(request:Request):
   user=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   if user[0]["type"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"user type not allowed"})
   await postgres_client.execute(query="delete from users where id=:id and type is null;",values={"id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/object-delete")
async def my_object_delete(request:Request,table:str):
   user=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   if user[0]["type"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"user type not allowed"})
   object=dict(request.query_params)
   object["created_by_id"]=f"=,{request.state.user['id']}"
   response=await create_where_string(postgres_column_datatype,object_serialize,object)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   where_string,where_value=response["message"][0],response["message"][1]
   query=f"delete from {table} {where_string};"
   await postgres_client.fetch_all(query=query,values=where_value)
   return {"status":1,"message":"done"}

#public
@app.post("/public/object-create")
async def public_object_create(request:Request,table:Literal["helpdesk","human"]):
   object=await request.json()
   object={k:v for k,v in object.items() if v}
   response=await postgres_crud("create",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.post("/public/object-create-form")
async def public_object_create_form(request:Request,table:Literal["helpdesk","human"],bucket:str=None,file_column:str="file_url"):
   form_data=await request.form()
   object={k:v for k,v in form_data.items() if k!="file"}
   file_list=form_data.getlist("file")
   file_list=[file for file in file_list if file.filename]
   if file_list:
      if not bucket:return responses.JSONResponse(status_code=400,content={"status":0,"message":"bucket missing"})
      response=await s3_file_upload(s3_client,s3_region_name,bucket,None,file_list)
      if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
      object[file_column]=",".join([v for k,v in response["message"].items()])
   response=await postgres_crud("create",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.post("/public/object-create-pdf-extract")
async def public_object_create_pdf_extract(request:Request,table:Literal["helpdesk","human"],pdf_column:str="description"):
   form_data=await request.form()
   object={k:v for k,v in form_data.items() if k!="file"}
   file_list=form_data.getlist("file")
   file_list=[file for file in file_list if file.filename]
   text=""
   for file in  file_list:
      if file.content_type!="application/pdf":return responses.JSONResponse(status_code=400,content={"status":0,"message":"wrong file type"})
      pdf_file=await file.read()
      doc=fitz.open(stream=pdf_file,filetype="pdf")
      for page in doc:text+=page.get_text("text")
      object[pdf_column]=text
   response=await postgres_crud("create",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response
   
@app.get("/public/object-read")
@cache(expire=60)
async def public_object_read(request:Request,table:str):
   if table not in ["users","post","project","atom"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   object=dict(request.query_params)
   response=await postgres_crud("read",table,[object],0,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.get("/public/otp-send-sns")
async def public_otp_send_sns(mobile:str,entity_id:str=None,sender_id:str=None,template_id:str=None,message:str=None):
   otp=random.randint(100000,999999)
   await postgres_client.execute(query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;",values={"otp":otp,"mobile":mobile})
   if not entity_id:output=sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   else:output=sns_client.publish(PhoneNumber=mobile,Message=message.replace("{otp}",str(otp)),MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return {"status":1,"message":output}

@app.get("/public/otp-send-ses")
async def public_otp_send_ses(sender:str,email:str):
   otp=random.randint(100000,999999)
   await postgres_client.fetch_all(query="insert into otp (otp,email) values (:otp,:email) returning *;",values={"otp":otp,"email":email})
   to,title,body=[email],"otp from atom",str(otp)
   ses_client.send_email(Source=sender,Destination={"ToAddresses":to},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return {"status":1,"message":"done"}

@app.get("/public/redis-get-object")
async def public_redis_get_object(key:str):
   output=await redis_client.get(key)
   if output:output=json.loads(output)
   return {"status":1,"message":output}

#private
@app.post("/private/file-upload-s3")
async def private_file_upload_s3(bucket:str,key:str,file:list[UploadFile]):
   key_list=None if key=="uuid" else key.split("---")
   response=await s3_file_upload(s3_client,s3_region_name,bucket,key_list,file)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.get("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(bucket:str,key:str):
   if "." not in key:return responses.JSONResponse(status_code=400,content={"status":0,"message":"extension must"})
   expiry_sec,size_kb=1000,100
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec,Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   return {"status":1,"message":output}

#admin
@app.get("/admin/object-read")
async def admin_object_read(request:Request,table:str):
   object=dict(request.query_params)
   response=await postgres_crud("read",table,[object],0,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   return response

@app.put("/admin/object-update")
async def admin_object_update(request:Request,table:str):
   object=await request.json()
   if postgres_schema.get(table,{}).get("updated_by_id",None):object["updated_by_id"]=request.state.user["id"]
   response=await postgres_crud("update",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return responses.JSONResponse(status_code=400,content=response)
   output=response["message"]
   #final
   return {"status":1,"message":output}

@app.get("/admin/delete-ids")
async def admin_delete_ids(table:str,ids:str):
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if len(ids.split(","))>100:return responses.JSONResponse(status_code=400,content={"status":0,"message":"max 100 ids allowed"})
   await postgres_client.execute(query=f"delete from {table} where id in ({ids});",values={})
   return {"status":1,"message":"done"}

@app.get("/admin/query-runner")
async def admin_query_runner(query:str):
  for item in ["insert","update","delete","alter","drop"]:
    if item in query:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{item} not allowed in query"})
  output=await postgres_client.fetch_all(query=query,values={})
  return {"status":1,"message":output}

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
         if message["type"]=="message" and message["channel"]==b'postgres_crud':
            data=json.loads(message['data'])
            try:
               response=await postgres_crud(data["mode"],data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
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
         if message.topic=="postgres_crud":
            data=json.loads(message.value.decode('utf-8'))
            try:
               response=await postgres_crud(data["mode"],data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
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
      response=loop.run_until_complete(postgres_crud(data["mode"],data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count))
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
      rabbitmq_channel.basic_consume("postgres_crud",aqmp_callback,auto_ack=True)
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
      lavinmq_channel.basic_consume("postgres_crud",aqmp_callback,auto_ack=True)
      lavinmq_channel.start_consuming()
   except KeyboardInterrupt:
      await postgres_client.disconnect()
      lavinmq_channel.close()
      lavinmq_client.close()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="lavinmq":
    try:asyncio.run(main_lavinmq())
    except KeyboardInterrupt:print("exit")