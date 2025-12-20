#import
from core.config import *
from core.function import *
import asyncio,json

#logic
async def logic():
   try:
      client_redis=await func_redis_client_read(config_redis_url_pubsub)
      client_redis_consumer=await func_redis_client_read_consumer(client_redis,config_channel_name)
      client_postgres_pool=await func_postgres_client_read(config_postgres_url)
      cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      async for message in client_redis_consumer.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            payload=json.loads(message['data'])
            if payload["func"]=="func_postgres_obj_list_create":asyncio.create_task(func_postgres_obj_list_create(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,payload["mode"],payload["table"],payload["obj_list"],payload["is_serialize"],payload["buffer"]))
            elif payload["func"]=="func_postgres_obj_list_update":asyncio.create_task(func_postgres_obj_list_update(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,payload["table"],payload["obj_list"],payload["is_serialize"],payload["created_by_id"]))
            print(f"{payload.get('func')} task created")
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
