#function
from function import function_rabbitmq_client_read_consumer,function_postgres_client_read
from function import function_postgres_object_create,function_postgres_object_update

#env
import os
from dotenv import load_dotenv
load_dotenv()

#config
config_rabbitmq_url=os.getenv("config_rabbitmq_url")
config_postgres_url=os.getenv("config_postgres_url")
config_channel_name=os.getenv("config_channel_name") or "channel_1"

#package
import asyncio,json,aio_pika

#logic
async def logic():
   try:
      async def aqmp_callback(message:aio_pika.IncomingMessage):
         async with message.process():
            payload=json.loads(message.body)
            function_name=payload["function"]
            if function_name=="function_postgres_object_create":
               asyncio.create_task(function_postgres_object_create(client_postgres_pool,payload["table"],payload["obj_list"]))
            elif function_name=="function_postgres_object_update":
               asyncio.create_task(function_postgres_object_update(client_postgres_pool,payload["table"],payload["obj_list"]))
            print(f"{payload.get('function')} task created")
      client_postgres_pool=await function_postgres_client_read(config_postgres_url)
      client_rabbitmq,client_rabbitmq_consumer=await function_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name)
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