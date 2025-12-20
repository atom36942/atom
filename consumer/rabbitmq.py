#import
from core.config import *
from core.function import *
import asyncio,json,aio_pika

#logic
async def logic():
   try:
      async def aqmp_callback(message:aio_pika.IncomingMessage):
         async with message.process():
            payload=json.loads(message.body)
            if payload["function"]=="func_postgres_obj_list_create":asyncio.create_task(func_postgres_obj_list_create(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,"now",payload["table"],payload["obj_list"],payload["is_serialize"]))
            elif payload["function"]=="func_postgres_obj_list_update":asyncio.create_task(func_postgres_obj_list_update(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,payload["table"],payload["obj_list"],payload["is_serialize"],payload["created_by_id"]))
            print(f"{payload.get('function')} task created")
      client_rabbitmq,client_rabbitmq_consumer=await func_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name)
      client_postgres_pool=await func_postgres_client_read(config_postgres_url)
      cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      await client_rabbitmq_consumer.consume(aqmp_callback)
      await asyncio.Future()
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      if client_rabbitmq_consumer:await client_rabbitmq_consumer.channel.close()
      if client_rabbitmq and not client_rabbitmq.is_closed: await client_rabbitmq.close()
      if client_postgres_pool: await client_postgres_pool.close()

#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")