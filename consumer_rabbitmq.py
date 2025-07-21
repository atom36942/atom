#function
from function import function_client_read_rabbitmq
from function import function_client_read_postgres,function_postgres_schema_read
from function import function_object_create_postgres,function_object_update_postgres,function_object_serialize

#config
import os
from dotenv import load_dotenv
load_dotenv()
config_rabbitmq_url=os.getenv("config_rabbitmq_url")
config_postgres_url=os.getenv("config_postgres_url")
config_channel_name="channel_1"

#import
import asyncio,json,aio_pika

#logic
async def logic():
   try:
      client_rabbitmq,client_rabbitmq_channel=await function_client_read_rabbitmq(config_rabbitmq_url)
      client_postgres=await function_client_read_postgres(config_postgres_url)
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      async def aqmp_callback(message:aio_pika.IncomingMessage):
         async with message.process():
            data=json.loads(message.body)
            if data["function"]=="function_object_create_postgres":asyncio.create_task(function_object_create_postgres(client_postgres,data["table"],data["object_list"],data.get("is_serialize",0),function_object_serialize,postgres_column_datatype))
            elif data["function"]=="function_object_update_postgres":asyncio.create_task(function_object_update_postgres(client_postgres,data["table"],data["object_list"],data.get("is_serialize",0),function_object_serialize,postgres_column_datatype))
            print(f"{data.get('function')} task created")
      queue=await client_rabbitmq_channel.declare_queue(config_channel_name,auto_delete=False)
      await queue.consume(aqmp_callback)
      await asyncio.Future()
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      await client_rabbitmq_channel.close()
      await client_rabbitmq.close()
      await client_postgres.disconnect()
   
#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")
