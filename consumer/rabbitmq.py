#config
from core.config import config_rabbitmq_url
from core.config import config_channel_name
from core.config import config_postgres_url

#function
from core.function import function_rabbitmq_client_read_consumer
from core.function import function_postgres_client_read,function_postgres_schema_read,function_postgres_object_serialize
from core.function import function_postgres_object_create,function_postgres_object_update

#package
import asyncio,json,aio_pika

#logic
async def logic():
   try:
      async def aqmp_callback(message:aio_pika.IncomingMessage):
         async with message.process():
            payload=json.loads(message.body)
            function_name=payload["function"]
            if function_name=="function_postgres_object_create":asyncio.create_task(function_postgres_object_create(client_postgres_pool,function_postgres_object_serialize,cache_postgres_column_datatype,"now",payload["table"],payload["obj_list"],payload["is_serialize"]))
            elif function_name=="function_postgres_object_update":
               asyncio.create_task(function_postgres_object_update(client_postgres_pool,payload["table"],payload["obj_list"]))
            print(f"{payload.get('function')} task created")
      client_rabbitmq,client_rabbitmq_consumer=await function_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name)
      client_postgres_pool=await function_postgres_client_read(config_postgres_url)
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      await client_rabbitmq_consumer.consume(aqmp_callback)
      await asyncio.Future()
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      if client_rabbitmq_consumer and hasattr(client_rabbitmq_consumer,'channel'): await client_rabbitmq_consumer.channel.close()
      if client_rabbitmq and not client_rabbitmq.is_closed: await client_rabbitmq.close()
      if client_postgres_pool: await client_postgres_pool.close()

#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")