#import
from core.config import *
from core.function import *
import asyncio,json

#logic
async def logic():
   try:
      client_kafka_consumer=await func_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_kafka_group_id,config_kafka_enable_auto_commit)
      client_postgres_pool=await func_postgres_client_read(config_postgres_url)
      cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      async for message in client_kafka_consumer:
         if message.topic==config_channel_name:
            payload=json.loads(message.value.decode('utf-8'))
            if payload["function"]=="func_postgres_obj_list_create":asyncio.create_task(func_postgres_obj_list_create(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,"now",payload["table"],payload["obj_list"],payload["is_serialize"]))
            elif payload["function"]=="func_postgres_obj_list_update":asyncio.create_task(func_postgres_obj_list_update(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,payload["table"],payload["obj_list"],payload["is_serialize"],payload["created_by_id"]))
            if not config_kafka_enable_auto_commit:await client_kafka_consumer.commit()
            print(f"{payload.get('function')} task created")
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      if client_kafka_consumer:await client_kafka_consumer.stop()
      if client_postgres_pool:await client_postgres_pool.close()
   
#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")
