#import
from core.config import *
from core.function import *
import asyncio
from celery import signals

#logger
import logging
logger=logging.getLogger(__name__)

#global
client_celery_consumer=func_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url)
client_postgres_pool,cache_postgres_schema,cache_postgres_column_datatype=None,None,None
worker_loop=None

#startup
@signals.worker_process_init.connect
def init_worker(**kwargs):
    global client_postgres_pool,cache_postgres_schema,cache_postgres_column_datatype,worker_loop
    worker_loop=asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)
    client_postgres_pool=worker_loop.run_until_complete(func_postgres_client_read(config_postgres_url))
    cache_postgres_schema,cache_postgres_column_datatype=worker_loop.run_until_complete(func_postgres_schema_read(client_postgres_pool))

#shutdown
@signals.worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    if client_postgres_pool and worker_loop:
        worker_loop.run_until_complete(client_postgres_pool.close())
        worker_loop.close()

#helper
from itertools import count
_run_counter=count(1)
def run_async(coro):
    n=next(_run_counter)
    if not client_postgres_pool or not worker_loop:raise RuntimeError("postgres pool not initialized")
    try:
        output=worker_loop.run_until_complete(coro)
        print(n)
        return None
    except Exception:
        logger.error(f"task failed #{n}",exc_info=True)
        raise
    
#task 1
@client_celery_consumer.task(name="func_postgres_obj_list_create")
def celery_task_1(mode,table,obj_list,is_serialize,buffer):
    return run_async(func_postgres_obj_list_create(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,mode,table,obj_list,is_serialize,buffer))

#task 2
@client_celery_consumer.task(name="func_postgres_obj_list_update")
def celery_task_2(table,obj_list,is_serialize,created_by_id):
    return run_async(func_postgres_obj_list_update(client_postgres_pool,func_postgres_obj_list_serialize,cache_postgres_column_datatype,table,obj_list,is_serialize,created_by_id))