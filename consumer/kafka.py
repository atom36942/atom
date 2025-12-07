#config
from config import config_kafka_url,config_kafka_username,config_kafka_password
from config import config_postgres_url
from config import config_channel_name
from config import config_kafka_group_id,config_kafka_enable_auto_commit

#function
from file.function import function_kafka_client_read_consumer,function_postgres_client_read
from file.function import function_postgres_object_create,function_postgres_object_update

#package
import asyncio,json

#logic
async def logic():
   try:
      client_kafka_consumer=await function_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_kafka_group_id,config_kafka_enable_auto_commit)
      client_postgres_pool=await function_postgres_client_read(config_postgres_url)
      async for message in client_kafka_consumer:
         if message.topic=="channel_1":
            payload=json.loads(message.value.decode('utf-8'))
            function_name=payload["function"]
            if function_name=="function_postgres_object_create":
               asyncio.create_task(function_postgres_object_create("now",client_postgres_pool,payload["table"],payload["obj_list"]))
            elif function_name=="function_postgres_object_update":
               asyncio.create_task(function_postgres_object_update(client_postgres_pool,payload["table"],payload["obj_list"]))
            if not config_kafka_enable_auto_commit:await client_kafka_consumer.commit()
            print(f"{payload.get('function')} task created")
   except asyncio.CancelledError:print("consumer cancelled")
   except Exception as e:print(str(e))
   finally:
      await client_kafka_consumer.stop()
      await client_postgres_pool.close()
   
#main
if __name__ == "__main__":
    try:asyncio.run(logic())
    except KeyboardInterrupt:print("exit")
