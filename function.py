#kafka consumer start
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

#redis subscriber start
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
      
#postgres add action count
async def postgres_add_action_count(postgres_client,action,object_list,object_table):
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

#postgres add creator key
async def postgres_add_creator_key(postgres_client,object_list):
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

#postgres create where
import hashlib,datetime
async def postgres_create_where(postgres_column_datatype,param):
   param={k:v for k,v in param.items() if k in postgres_column_datatype}
   param={k:v for k,v in param.items() if k not in ["table","order","limit","page"]}
   param={k:v for k,v in param.items() if k not in ["location","metadata"]}
   where_operator={k:v.split(',',1)[0] for k,v in param.items()}
   where_value={k:v.split(',',1)[1] for k,v in param.items()}
   key_list=[f"({k} {where_operator[k]} :{k} or :{k} is null)" for k,v in where_value.items()]
   key_joined=' and '.join(key_list)
   where_string=f"where {key_joined}" if key_joined else ""
   for k,v in where_value.items():
      if k in postgres_column_datatype:datatype=postgres_column_datatype[k]
      else:return {"status":0,"message":f"{k} column not in postgres_column_datatype"}
      if k in ["password","google_id"]:where_value[k]=hashlib.sha256(v.encode()).hexdigest() if v else None
      if "int" in datatype:where_value[k]=int(v) if v else None
      if datatype in ["numeric"]:where_value[k]=round(float(v),3) if v else None
      if "time" in datatype:where_value[k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
      if datatype in ["date"]:where_value[k]=datetime.datetime.strptime(v,'%Y-%m-%dT%H:%M:%S') if v else None
      if datatype in ["ARRAY"]:where_value[k]=v.split(",") if v else None
   return {"status":1,"message":[where_string,where_value]}

#postgres crud
import hashlib,datetime,json
async def postgres_crud(postgres_client,postgres_column_datatype,is_serialize,mode,table,object_list):
   #mode
   if mode=="create":
      column_to_insert_list=[*object_list[0]]
      query=f"insert into {table} ({','.join(column_to_insert_list)}) values ({','.join([':'+item for item in column_to_insert_list])}) on conflict do nothing returning *;"
   if mode=="update":
      column_to_update_list=[*object_list[0]]
      column_to_update_list.remove("id")
      query=f"update {table} set {','.join([f'{item}=coalesce(:{item},{item})' for item in column_to_update_list])} where id=:id returning *;"
   if mode=="delete":
      query=f"delete from {table} where id=:id;"
   #serialize
   if is_serialize==1:
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
   #execute
   if len(object_list)>1:output=await postgres_client.execute_many(query=query,values=object_list)
   else:output=await postgres_client.execute(query=query,values=object_list[0])
   #final
   return {"status":1,"message":output}
   