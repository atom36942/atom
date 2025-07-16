#function
from function import *

#logic
import asyncio,json,os
async def function_consumer_redis_postgres_crud():
   config_redis_url=os.getenv("config_redis_url")
   config_channel_name=os.getenv("config_channel_name","ch1")
   config_postgres_url=os.getenv("config_postgres_url")

   client_redis=await function_client_read_redis(config_redis_url)
   redis_consumer_client=await function_client_read_redis_consumer(client_redis,config_channel_name)
   client_postgres=await function_client_read_postgres(config_postgres_url)
   postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
   try:
      async for message in redis_consumer_client.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            data=json.loads(message['data'])
            try:
               if data["mode"]=="create":output=await function_postgres_object_create_serialize(data["table"],[data["object"]],client_postgres,data["is_serialize"],function_postgres_object_serialize,postgres_column_datatype)   
               elif data["mode"]=="update":output=await function_postgres_object_update(data["table"],[data["object"]],client_postgres,data["is_serialize"],function_postgres_object_serialize,postgres_column_datatype)
               print(output)
            except Exception as e:print(str(e))
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await client_postgres.disconnect()
      await redis_consumer_client.unsubscribe(config_channel_name)
      await client_redis.aclose()

import asyncio
if __name__ == "__main__":
    try:asyncio.run(function_consumer_redis_postgres_crud())
    except KeyboardInterrupt:print("exit")
