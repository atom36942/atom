#function
from function import function_celery_client_read_consumer
from function import function_client_read_postgres,function_postgres_schema_read
from function import function_object_create_postgres,function_object_update_postgres,function_object_serialize
from function import function_postgres_query_runner

#env
import os
from dotenv import load_dotenv
load_dotenv()

#config
config_celery_broker_url=os.getenv("config_celery_broker_url")
config_celery_backend_url=os.getenv("config_celery_backend_url")
config_postgres_url=os.getenv("config_postgres_url")

#package
import asyncio,traceback
from celery import signals

#client
client_celery_consumer=function_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url)
client_postgres=None
postgres_schema=None
postgres_column_datatype=None

#startup
@signals.worker_process_init.connect
def init_worker(**kwargs):
    global client_postgres,postgres_schema,postgres_column_datatype
    loop=asyncio.get_event_loop()
    client_postgres=loop.run_until_complete(function_client_read_postgres(config_postgres_url))
    postgres_schema,postgres_column_datatype=loop.run_until_complete(function_postgres_schema_read(client_postgres))

#shutdown
@signals.worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global client_postgres
    loop=asyncio.get_event_loop()
    loop.run_until_complete(client_postgres.disconnect())

#task 1
@client_celery_consumer.task(name="function_object_create_postgres")
def celery_task_1(table,object_list,is_serialize):
    try:
        global client_postgres
        def run_wrapper():
            async def wrapper():await function_object_create_postgres(client_postgres,table,object_list,is_serialize,function_object_serialize,postgres_column_datatype)
            loop=asyncio.get_event_loop()
            return loop.run_until_complete(wrapper())
        run_wrapper()
        return None
    except Exception as e:
        print("Exception occurred:",str(e))
        traceback.print_exc()
        return None

#task 2
@client_celery_consumer.task(name="function_object_update_postgres")
def celery_task_2(table,object_list,is_serialize):
    try:
        global client_postgres
        def run_wrapper():
            async def wrapper():await function_object_update_postgres(client_postgres,table,object_list,is_serialize,function_object_serialize,postgres_column_datatype)
            loop=asyncio.get_event_loop()
            return loop.run_until_complete(wrapper())
        run_wrapper()
        return None
    except Exception as e:
        print("Exception occurred:",str(e))
        traceback.print_exc()
        return None
    
#task 3
@client_celery_consumer.task(name="function_postgres_query_runner")
def celery_task_3(query):
    try:
        global client_postgres
        print("done")
        def run_wrapper():
            async def wrapper():await function_postgres_query_runner(client_postgres,query)
            loop=asyncio.get_event_loop()
            return loop.run_until_complete(wrapper())
        run_wrapper()
        return None
    except Exception as e:
        print("Exception occurred:",str(e))
        traceback.print_exc()
        return None