async def postgres_schema_read(postgres_client):
   postgres_schema={}
   query='''
   WITH t AS (SELECT * FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'), 
   c AS (
   SELECT table_name, column_name, data_type, 
   CASE WHEN is_nullable = 'YES' THEN 1 ELSE 0 END AS is_nullable, 
   column_default 
   FROM information_schema.columns 
   WHERE table_schema='public'
   ), 
   i AS (
   SELECT t.relname::text AS table_name, a.attname AS column_name, 
   CASE WHEN idx.indisprimary OR idx.indisunique OR idx.indisvalid THEN 1 ELSE 0 END AS is_index
   FROM pg_attribute a
   JOIN pg_class t ON a.attrelid = t.oid
   JOIN pg_namespace ns ON t.relnamespace = ns.oid
   LEFT JOIN pg_index idx ON a.attrelid = idx.indrelid AND a.attnum = ANY(idx.indkey)
   WHERE ns.nspname = 'public' AND a.attnum > 0 AND t.relkind = 'r'
   )
   SELECT t.table_name as table, c.column_name as column, c.data_type as datatype,c.column_default as default, c.is_nullable as is_null, COALESCE(i.is_index, 0) AS is_index 
   FROM t 
   LEFT JOIN c ON t.table_name = c.table_name 
   LEFT JOIN i ON t.table_name = i.table_name AND c.column_name = i.column_name;
   '''
   output=await postgres_client.fetch_all(query=query,values={})
   for object in output:
      table,column=object["table"],object["column"]
      column_data={"datatype": object["datatype"],"default": object["default"],"is_null": object["is_null"],"is_index": object["is_index"]}
      if table not in postgres_schema:postgres_schema[table]={}
      postgres_schema[table][column]=column_data
   return postgres_schema
      
async def postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list:return {"status":0,"message":"object null issue"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   column_insert_list=[*object_list[0]]
   query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   if len(object_list)==1:output=await postgres_client.execute(query=query,values=object_list[0])
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
   return {"status":1,"message":output}

async def postgres_update(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list:return {"status":0,"message":"object null issue"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=coalesce(:{item},{item})' for item in column_update_list])} where id=:id returning *;"
   if len(object_list)==1:output=await postgres_client.execute(query=query,values=object_list[0])
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
   return {"status":1,"message":output}

async def postgres_delete(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if not object_list:return {"status":0,"message":"object null issue"}
   if is_serialize:
      response=await object_serialize(postgres_column_datatype,object_list)
      if response["status"]==0:return response
      object_list=response["message"]
   query=f"delete from {table} where id=:id;"
   if len(object_list)==1:output=await postgres_client.execute(query=query,values=object_list[0])
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
   return {"status":1,"message":output}

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

async def postgres_transaction(postgres_client,query_value_list):
   try:
      transaction=await postgres_client.transaction()
      output=[await postgres_client.fetch_all(query=item[0],values=item[1]) for item in query_value_list]
   except Exception as e:
      await transaction.rollback()
      return {"status":0,"message":e.args}
   else:
      await transaction.commit()
   return {"status":1,"message":output}

async def postgres_schema_init(postgres_client,postgres_schema_read,config):
   #extension
   await postgres_client.fetch_all(query="create extension if not exists postgis;",values={})
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
   for table,column_list in config["table"].items():
      for column in column_list:
         column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
         index_name=f"index_{table}_{column_name}"
         is_index=postgres_schema.get(table,{}).get(column_name,{}).get("is_index",None)
         if column_index_type=="0" and is_index==1:await postgres_client.execute(query=f"drop index if exists {index_name};",values={})
         if column_index_type!="0" and is_index==0:await postgres_client.execute(query=f"create index concurrently if not exists {index_name} on {table} using {column_index_type} ({column_name});",values={})
   #query
   constraint_name_list={object["constraint_name"] for object in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))}
   for query in config["query"].values():
      if "add constraint" in query and query.split()[5] in constraint_name_list:continue
      await postgres_client.fetch_all(query=query,values={})
   #match column
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,columns in postgres_schema.items():
      if table in config["table"]:
         existing_columns={col.split("-")[0] for col in config["table"][table]}
         for column_name in columns:
            if column_name != "id" and column_name not in existing_columns:
               await postgres_client.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column_name};")
               await postgres_client.execute(f"DROP INDEX IF EXISTS index_{table}_{column_name};")
   #final
   return {"status":1,"message":"done"}

async def postgres_schema_init_auto(postgres_client,postgres_schema_read):
   #created_at default
   query="DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='created_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;"
   await postgres_client.execute(query=query,values={})
   #updated_at default
   query="create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';"
   await postgres_client.execute(query=query,values={})
   query="DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name = 'updated_at' AND table_schema = 'public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;"
   await postgres_client.execute(query=query,values={})
   #is_protected
   query="DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected = 1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;"
   await postgres_client.execute(query=query,values={})
   #root user
   postgres_schema=await postgres_schema_read(postgres_client)
   if postgres_schema.get("users",{}) and postgres_schema.get("users",{}).get("type",None) and postgres_schema.get("users",{}).get("username",None) and postgres_schema.get("users",{}).get("password",None):
      query="insert into users (type,username,password) values ('admin','atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3') on conflict do nothing;"
      await postgres_client.execute(query=query,values={})
      query="create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;"
      await postgres_client.execute(query=query,values={})
   #bulk delete disable
   postgres_schema=await postgres_schema_read(postgres_client)
   if postgres_schema.get("users",{}):
      query="create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;"
      await postgres_client.execute(query=query,values={})
      query="create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);"
      await postgres_client.execute(query=query,values={})
   #log password
   postgres_schema=await postgres_schema_read(postgres_client)
   if "log_password" in postgres_schema:
      query="CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;"
      await postgres_client.execute(query=query,values={})
      query="CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();"
      await postgres_client.execute(query=query,values={})
   #final
   return {"status":1,"message":"done"}

async def postgres_clean_creator(postgres_client,postgres_schema_read):
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column in postgres_schema.items():
      if column.get("created_by_id",None):
         query=f"delete from {table} where created_by_id not in (select id from users);"
         await postgres_client.execute(query=query,values={})
   return {"status":1,"message":"done"}

async def postgres_clean_parent(postgres_client,postgres_schema_read):
   postgres_schema=await postgres_schema_read(postgres_client)
   for table,column in postgres_schema.items():
      if column.get("parent_table",None) and column.get("parent_id",None):
         output=await postgres_client.fetch_all(query=f"select distinct(parent_table) from {table};",values={})
         parent_table_list=[item['parent_table'] for item in output]
         for parent_table in parent_table_list:
            if parent_table not in postgres_schema:return {"status":0,"message":f"{table} has invalid parent_table {parent_table}"}
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
      file_stream=BytesIO(file_content)
      s3_client.upload_fileobj(file_stream,bucket,key)
      output[file.filename]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
      file.file.close()
   return {"status":1,"message":output}

from fastapi import responses
def error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})

import csv,io
async def file_to_object_list(file):
   content=await file.read()
   csv_text=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(csv_text))
   object_list=[row for row in reader]
   await file.close()
   return object_list
