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
            output=await func_wrapper_consumer(payload,func_postgres_obj_list_create,func_postgres_obj_list_update,func_postgres_obj_list_serialize,client_postgres_pool,cache_postgres_column_datatype)
            print(output)
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