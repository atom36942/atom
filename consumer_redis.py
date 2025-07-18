#function
from function import function_client_read_redis,function_client_read_redis_consumer
from function import function_client_read_postgres,function_postgres_schema_read
from function import function_postgres_object_create,function_postgres_object_serialize

#config
import os
from dotenv import load_dotenv
load_dotenv()
config_redis_url=os.getenv("config_redis_url")
config_channel_name=os.getenv("config_channel_name","ch1")
config_postgres_url=os.getenv("config_postgres_url")

#logic
import asyncio,json,os
async def main_redis_consumer():
   client_redis=await function_client_read_redis(config_redis_url)
   client_redis_consumer=await function_client_read_redis_consumer(client_redis,config_channel_name)
   client_postgres=await function_client_read_postgres(config_postgres_url)
   postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
   try:
      async for message in client_redis_consumer.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            data=json.loads(message['data'])
            if data.get("function")=="postgres_create":asyncio.create_task(function_postgres_object_create(data["param"]["table"],[data["param"]["object"]],client_postgres,data["param"]["is_serialize"],function_postgres_object_serialize,postgres_column_datatype))
            print(f"{data.get('function')} task created")
   except asyncio.CancelledError:print("subscription cancelled")
   except Exception as e:print(str(e))
   finally:
      await client_redis.aclose()
      await client_redis_consumer.unsubscribe(config_channel_name)
      await client_postgres.disconnect()
      
import asyncio
if __name__ == "__main__":
    try:asyncio.run(main_redis_consumer())
    except KeyboardInterrupt:print("exit")
