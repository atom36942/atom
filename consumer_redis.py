#function
from function import function_client_read_redis,function_client_read_redis_consumer
from function import function_client_read_postgres,function_postgres_schema_read
from function import function_object_create_postgres,function_object_update_postgres,function_object_serialize

#config
import os
from dotenv import load_dotenv
load_dotenv()
config_redis_url=os.getenv("config_redis_url")
config_postgres_url=os.getenv("config_postgres_url")
config_channel_name="channel_1"

#import
import asyncio,json

#logic
async def logic():
   try:
      client_redis=await function_client_read_redis(config_redis_url)
      client_redis_consumer=await function_client_read_redis_consumer(client_redis,config_channel_name)
      client_postgres=await function_client_read_postgres(config_postgres_url)
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      async for message in client_redis_consumer.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            payload=json.loads(message['payload'])
            if payload["function"]=="function_object_create_postgres":asyncio.create_task(function_object_create_postgres(client_postgres,payload["table"],payload["object_list"],payload.get("is_serialize",0),function_object_serialize,postgres_column_datatype))
            elif payload["function"]=="function_object_update_postgres":asyncio.create_task(function_object_update_postgres(client_postgres,payload["table"],payload["object_list"],payload.get("is_serialize",0),function_object_serialize,postgres_column_datatype))
            print(f"{payload.get('function')} task created")
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      await client_redis.aclose()
      await client_redis_consumer.unsubscribe(config_channel_name)
      await client_postgres.disconnect()
      
#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")
