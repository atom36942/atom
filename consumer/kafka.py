#function
from file.function import function_kafka_client_read_consumer,function_postgres_client_read
from file.function import function_postgres_object_create,function_postgres_object_update

#env
import os
from dotenv import load_dotenv
load_dotenv()

#config
config_kafka_url=os.getenv("config_kafka_url")
config_kafka_username=os.getenv("config_kafka_username")
config_kafka_password=os.getenv("config_kafka_password")
config_postgres_url=os.getenv("config_postgres_url")
config_channel_name=os.getenv("config_channel_name") or "channel_1"
config_group_id=os.getenv("config_group_id") or "group_1"
config_enable_auto_commit = (os.getenv("config_enable_auto_commit") or "True").lower() == "true"

#package
import asyncio,json

#logic
async def logic():
   try:
      client_kafka_consumer=await function_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_group_id,config_enable_auto_commit)
      client_postgres_pool=await function_postgres_client_read(config_postgres_url)
      async for message in client_kafka_consumer:
         if message.topic=="channel_1":
            payload=json.loads(message.value.decode('utf-8'))
            function_name=payload["function"]
            if function_name=="function_postgres_object_create":
               asyncio.create_task(function_postgres_object_create(client_postgres_pool,payload["table"],payload["obj_list"]))
            elif function_name=="function_postgres_object_update":
               asyncio.create_task(function_postgres_object_update(client_postgres_pool,payload["table"],payload["obj_list"]))
            if not config_enable_auto_commit:await client_kafka_consumer.commit()
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
