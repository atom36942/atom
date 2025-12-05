#config
import os
from dotenv import load_dotenv
load_dotenv()
config_redis_url_pubsub=os.getenv("config_redis_url_pubsub")
config_postgres_url=os.getenv("config_postgres_url")
config_channel_name=os.getenv("config_channel_name") or "channel_1"

#function
from file.function import function_redis_client_read,function_redis_client_read_consumer,function_postgres_client_read
from file.function import function_postgres_object_create,function_postgres_object_update

#package
import asyncio,json

#logic
async def logic():
   try:
      client_redis=await function_redis_client_read(config_redis_url_pubsub)
      client_redis_consumer=await function_redis_client_read_consumer(client_redis,config_channel_name)
      client_postgres_pool=await function_postgres_client_read(config_postgres_url)
      async for message in client_redis_consumer.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            payload=json.loads(message['data'])
            function_name=payload["function"]
            if function_name=="function_postgres_object_create":
               asyncio.create_task(function_postgres_object_create("now",client_postgres_pool,payload["table"],payload["obj_list"]))
            elif function_name=="function_postgres_object_update":
               asyncio.create_task(function_postgres_object_update(client_postgres_pool,payload["table"],payload["obj_list"]))
            print(f"{payload.get('function')} task created")
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      await client_redis.aclose()
      await client_redis_consumer.unsubscribe(config_channel_name)
      await client_postgres_pool.close()
      
#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")
