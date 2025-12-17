#config
from core.config import config_redis_url_pubsub
from core.config import config_channel_name
from core.config import config_postgres_url

#function
from core.function import function_redis_client_read,function_redis_client_read_consumer
from core.function import function_postgres_client_read,function_postgres_schema_read,function_postgres_object_serialize
from core.function import function_postgres_object_create,function_postgres_object_update

#package
import asyncio,json

#logic
async def logic():
   try:
      client_redis=await function_redis_client_read(config_redis_url_pubsub)
      client_redis_consumer=await function_redis_client_read_consumer(client_redis,config_channel_name)
      client_postgres_pool=await function_postgres_client_read(config_postgres_url)
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      async for message in client_redis_consumer.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            payload=json.loads(message['data'])
            function_name=payload["function"]
            if function_name=="function_postgres_object_create":asyncio.create_task(function_postgres_object_create(client_postgres_pool,function_postgres_object_serialize,cache_postgres_column_datatype,"now",payload["table"],payload["obj_list"],payload["is_serialize"]))
            elif function_name=="function_postgres_object_update":asyncio.create_task(function_postgres_object_update(client_postgres_pool,payload["table"],payload["obj_list"]))
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
