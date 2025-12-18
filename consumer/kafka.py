#config
from core.config import config_kafka_url,config_kafka_username,config_kafka_password
from core.config import config_channel_name,config_kafka_group_id,config_kafka_enable_auto_commit
from core.config import config_postgres_url

#function
from core.function import function_kafka_client_read_consumer
from core.function import function_postgres_client_read,function_postgres_schema_read,function_postgres_object_serialize
from core.function import function_postgres_object_create,function_postgres_object_update

#package
import asyncio,json

#logic
async def logic():
   try:
      client_kafka_consumer=await function_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_kafka_group_id,config_kafka_enable_auto_commit)
      client_postgres_pool=await function_postgres_client_read(config_postgres_url)
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None, None)
      async for message in client_kafka_consumer:
         if message.topic==config_channel_name:
            payload=json.loads(message.value.decode('utf-8'))
            function_name=payload["function"]
            if function_name=="function_postgres_object_create":asyncio.create_task(function_postgres_object_create(client_postgres_pool,function_postgres_object_serialize,cache_postgres_column_datatype,"now",payload["table"],payload["obj_list"],payload["is_serialize"]))
            elif function_name=="function_postgres_object_update":asyncio.create_task(function_postgres_object_update(client_postgres_pool,function_postgres_object_serialize,cache_postgres_column_datatype,payload["table"],payload["obj_list"],payload["is_serialize"],None))
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
