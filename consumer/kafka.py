#function
from function import function_kafka_client_read_consumer
from function import function_postgres_client_pool_read,function_postgres_schema_read
from function import function_object_create_postgres,function_object_update_postgres,function_object_serialize
from function import function_postgres_query_runner

#env
import os
from dotenv import load_dotenv
load_dotenv()

#config
config_kafka_url=os.getenv("config_kafka_url")
config_kafka_username=os.getenv("config_kafka_username")
config_kafka_password=os.getenv("config_kafka_password")
config_postgres_url=os.getenv("config_postgres_url")
config_channel_name=os.getenv("config_channel_name") or "channel_1"
config_group_id=os.getenv("config_group_id") or "group_1"
config_enable_auto_commit = (os.getenv("config_enable_auto_commit") or "True").lower() == "true"

#package
import asyncio,json

#logic
async def logic():
   try:
      client_kafka_consumer=await function_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_group_id,config_enable_auto_commit)
      client_postgres_pool=await function_postgres_client_pool_read(config_postgres_url)
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres_pool)
      async for message in client_kafka_consumer:
         if message.topic=="channel_1":
            payload=json.loads(message.value.decode('utf-8'))
            if payload["function"]=="function_object_create_postgres":asyncio.create_task(function_object_create_postgres(client_postgres_pool,payload["table"],payload["object_list"],payload.get("is_serialize",0),function_object_serialize,postgres_column_datatype))
            elif payload["function"]=="function_object_update_postgres":asyncio.create_task(function_object_update_postgres(client_postgres_pool,payload["table"],payload["object_list"],payload.get("is_serialize",0),function_object_serialize,postgres_column_datatype))
            elif payload["function"]=="function_postgres_query_runner":asyncio.create_task(function_postgres_query_runner(client_postgres_pool,payload["mode"],payload["query"]))
            if not config_enable_auto_commit:await client_kafka_consumer.commit()
            print(f"{payload.get('function')} task created")
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      await client_kafka_consumer.stop()
      await client_postgres_pool.disconnect()
   
#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")
