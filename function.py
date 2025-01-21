async def read_postgres_schema(postgres_client):
   postgres_schema={}
   [postgres_schema.setdefault(item["table_name"],{}).update({item["column_name"]:{"datatype":item["data_type"], "nullable":item["is_nullable"], "default":item["column_default"]}}) for item in await postgres_client.fetch_all(query='''with t as (select * from information_schema.tables where table_schema='public' and table_type='BASE TABLE'),c as (select * from information_schema.columns where table_schema='public')select t.table_name,c.column_name,c.data_type,c.is_nullable,c.column_default from t left join c on t.table_name=c.table_name''', values={})]
   return postgres_schema
    
async def queue_pull(data,postgres_cud,postgres_client,object_serialize,postgres_column_datatype):
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

import json
async def queue_push(queue,channel,data,redis_client,rabbitmq_channel,lavinmq_channel,kafka_producer_client):
   if queue=="redis":output=await redis_client.publish(channel,json.dumps(data))
   if queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=channel,body=json.dumps(data))
   if queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=channel,body=json.dumps(data))
   if queue=="kafka":output=await kafka_producer_client.send_and_wait(channel,json.dumps(data,indent=2).encode('utf-8'),partition=0)
   return output

async def login_access_check(request,user):
   query_param=dict(request.query_params)
   if query_param.get("is_exist",None)=="1":
      if not user:return {"status":0,"message":"no user"}
   if query_param.get("is_admin",None)=="1":
      if not user:return {"status":0,"message":"no user"}
      if user["api_access"] in [None,""," "]:return {"status":0,"message":"user not admin"}
   if query_param.get("type",None):
      if not user:return {"status":0,"message":"no user"}
      if user["type"]!=query_param["type"]:return {"status":0,"message":"user type mismatch"}
   if query_param.get("is_active",None):
      if not user:return {"status":0,"message":"no user"}
      if user["is_active"]==0:return {"status":0,"message":"user not active"}
   return {"status":1,"message":"done"}

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

import jwt,json,time
async def create_token(user,secret_key_jwt):
   data=json.dumps({"id":user["id"]},default=str)
   token=jwt.encode({"exp":time.time()+1000000000000,"data":data},secret_key_jwt)
   return {"status":1,"message":token}

object_list_log=[]
async def create_api_log(postgres_client,user,request,response,response_time_ms):
   global object_list_log
   object={"created_by_id":user["id"] if user else None,"api":request.url.path,"status_code":response.status_code,"response_time_ms":response_time_ms}
   object_list_log.append(object)
   if len(object_list_log)>=3:
      query="insert into log_api (created_by_id,api,status_code,response_time_ms) values (:created_by_id,:api,:status_code,:response_time_ms);"
      await postgres_client.execute_many(query=query,values=object_list_log)
      object_list_log=[]
   return None

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

async def postgres_schema_init(postgres_client,read_postgres_schema,config):
   #extension
   for extension in config["extension"]:await postgres_client.execute(f"create extension if not exists {extension}",values={})
   #table
   postgres_schema=await read_postgres_schema(postgres_client)
   for table in config["table"]:
      if table not in postgres_schema:
         await postgres_client.execute(f"create table if not exists {table} (id bigint primary key generated always as identity not null);", values={})
   #column
   postgres_schema=await read_postgres_schema(postgres_client)
   for k,v in config["column"].items():
      for table in v[1]:
         if not postgres_schema.get(table,{}).get(k,None):
            await postgres_client.execute(f"alter table {table} add column if not exists {k} {v[0]};", values={})
   #not null
   postgres_schema=await read_postgres_schema(postgres_client)
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
   #final
   return {"status":1,"message":"done"}