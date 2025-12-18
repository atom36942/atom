#config
from core.config import config_celery_broker_url,config_celery_backend_url
from core.config import config_postgres_url

#function
from core.function import function_celery_client_read_consumer
from core.function import function_postgres_client_read,function_postgres_schema_read,function_postgres_object_serialize
from core.function import function_postgres_object_create,function_postgres_object_update

#package
import asyncio,traceback
from celery import signals

#client
client_celery_consumer=function_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url)
client_postgres_pool=None

#startup
@signals.worker_process_init.connect
def init_worker(**kwargs):
    global client_postgres_pool,cache_postgres_schema,cache_postgres_column_datatype
    loop=asyncio.get_event_loop()
    client_postgres_pool=loop.run_until_complete(function_postgres_client_read(config_postgres_url))
    cache_postgres_schema,cache_postgres_column_datatype=loop.run_until_complete(function_postgres_schema_read(client_postgres_pool))

#shutdown
@signals.worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global client_postgres_pool
    loop=asyncio.get_event_loop()
    loop.run_until_complete(client_postgres_pool.close())

#task 1
@client_celery_consumer.task(name="function_postgres_object_create")
def celery_task_1(table,obj_list,is_serialize):
    try:
        global client_postgres_pool
        def run_wrapper():
            async def wrapper():await function_postgres_object_create(client_postgres_pool,function_postgres_object_serialize,cache_postgres_column_datatype,"now",table,obj_list,is_serialize)
            loop=asyncio.get_event_loop()
            return loop.run_until_complete(wrapper())
        run_wrapper()
        return None
    except Exception as e:
        print("Exception occurred:",str(e))
        traceback.print_exc()
        return None

#task 2
@client_celery_consumer.task(name="function_postgres_object_update")
def celery_task_2(table,obj_list,is_serialize):
    try:
        global client_postgres_pool
        def run_wrapper():
            async def wrapper():await function_postgres_object_update(client_postgres_pool,function_postgres_object_serialize,cache_postgres_column_datatype,table,obj_list,is_serialize,None)
            loop=asyncio.get_event_loop()
            return loop.run_until_complete(wrapper())
        run_wrapper()
        return None
    except Exception as e:
        print("Exception occurred:",str(e))
        traceback.print_exc()
        return None
    
    
