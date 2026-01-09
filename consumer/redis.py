#import
from core.function import *
from core.config import *
import asyncio,json
#logic
async def logic():
   try:
      client_redis=await func_redis_client_read(config_redis_url_pubsub)
      client_redis_consumer=await func_redis_client_read_consumer(client_redis,config_channel_name)
      client_postgres_pool=await func_postgres_client_read(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
      cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      async for message in client_redis_consumer.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            payload=json.loads(message['data'])
            await func_handler_consumer(payload,func_postgres_obj_create,func_postgres_obj_update,func_postgres_obj_serialize,client_postgres_pool,cache_postgres_column_datatype)
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
